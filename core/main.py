import time
import json
import logging
import os
import click
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import uvicorn

from registry import registry
from database import init_db, get_db, save_metric, Metric, Agent, User
from models import MetricPayload, MetricsBatch, LoginRequest
from auth import verify_password, get_password_hash, create_access_token, get_current_user

logger = logging.getLogger(__name__)

def create_app():
    app = FastAPI(title="Metrics Collector Core")

    @app.on_event("startup")
    def startup():
        init_db()
        # Создание администратора по умолчанию
        db = next(get_db())
        admin = db.query(User).filter(User.login == "admin").first()
        if not admin:
            admin_pass = os.getenv("ADMIN_PASSWORD", "admin")
            hashed = get_password_hash(admin_pass)
            admin = User(login="admin", password_hash=hashed, role="admin", created_at=int(time.time()))
            db.add(admin)
            db.commit()
            print(f"Default admin created (login: admin, password: {admin_pass})")
        db.close()
        logger.info("Core started, database initialized.")

    # --- Эндпоинты авторизации ---
    @app.post("/api/auth/register")
    def register(req: LoginRequest, db=Depends(get_db)):
        existing = db.query(User).filter(User.login == req.login).first()
        if existing:
            raise HTTPException(status_code=400, detail="Login already exists")
        hashed = get_password_hash(req.password)
        user = User(login=req.login, password_hash=hashed, role="user", created_at=int(time.time()))
        db.add(user)
        db.commit()
        return {"msg": "User created"}

    @app.post("/api/auth/login")
    def login(req: LoginRequest, db=Depends(get_db)):
        user = db.query(User).filter(User.login == req.login).first()
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        access_token = create_access_token(data={"sub": user.login, "role": user.role})
        return {"access_token": access_token, "token_type": "bearer", "role": user.role, "login": user.login}

    @app.get("/api/auth/me")
    def get_me(current_user: User = Depends(get_current_user)):
        return {"login": current_user.login, "role": current_user.role}

    # --- Защищённый эндпоинт для получения метрик ---
    @app.get("/api/v1/metrics/query")
    def query_metrics(
        limit: int = 100,
        offset: int = 0,
        sort: str = "desc",
        agent: str = None,
        metric_name: str = None,
        from_time: int = None,
        to_time: int = None,
        current_user: User = Depends(get_current_user),
        db=Depends(get_db)
    ):
        query = db.query(Metric)
        if agent:
            query = query.filter(Metric.agent_id == agent)
        if metric_name:
            query = query.filter(Metric.name == metric_name)
        if from_time:
            query = query.filter(Metric.timestamp >= from_time)
        if to_time:
            query = query.filter(Metric.timestamp <= to_time)
        if sort == "desc":
            query = query.order_by(Metric.timestamp.desc())
        else:
            query = query.order_by(Metric.timestamp.asc())
        total = query.count()
        metrics = query.offset(offset).limit(limit).all()
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "metrics": [
                {
                    "agent_id": m.agent_id,
                    "name": m.name,
                    "value": m.value,
                    "timestamp": m.timestamp,
                    "tags": json.loads(m.tags) if m.tags else {}
                } for m in metrics
            ]
        }

    # --- Эндпоинты приёма метрик (открытые) ---
    @app.post("/api/v1/metrics")
    def receive_metrics(payload: MetricPayload):
        ts = payload.timestamp
        for name, value in payload.metrics.items():
            save_metric(payload.agent_id, ts, name, value, payload.tags)
            registry.set_gauge(name, value, {**payload.tags, "agent": payload.agent_id})
        logger.info(f"Received {len(payload.metrics)} metrics from {payload.agent_id}")
        return {"status": "ok", "received": len(payload.metrics)}

    @app.post("/api/v1/metrics/batch")
    def receive_metrics_batch(batch: MetricsBatch):
        total = 0
        for payload in batch.batch:
            ts = payload.timestamp
            for name, value in payload.metrics.items():
                save_metric(payload.agent_id, ts, name, value, payload.tags)
                registry.set_gauge(name, value, {**payload.tags, "agent": payload.agent_id})
                total += 1
        logger.info(f"Received batch with {len(batch.batch)} payloads, total {total} metrics")
        return {"status": "ok", "received": total}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    payload_data = json.loads(data)
                    payload = MetricPayload(**payload_data)
                    ts = payload.timestamp
                    for name, value in payload.metrics.items():
                        save_metric(payload.agent_id, ts, name, value, payload.tags)
                        registry.set_gauge(name, value, {**payload.tags, "agent": payload.agent_id})
                    await websocket.send_text("ok")
                except Exception as e:
                    await websocket.send_text(f"error: {str(e)}")
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")

    @app.get("/metrics")
    def prometheus_metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/v1/agents")
    def list_agents(db=Depends(get_db)):
        agents = db.query(Agent).order_by(Agent.last_seen.desc()).all()
        return [{"agent_id": a.agent_id, "last_seen": a.last_seen, "hostname": a.hostname, "ip": a.ip} for a in agents]

    @app.get("/api/v1/history")
    def get_history(metric: str, from_ts: int = None, to_ts: int = None, limit: int = 1000, db=Depends(get_db)):
        query = db.query(Metric).filter(Metric.name == metric)
        if from_ts:
            query = query.filter(Metric.timestamp >= from_ts)
        if to_ts:
            query = query.filter(Metric.timestamp <= to_ts)
        rows = query.order_by(Metric.timestamp.desc()).limit(limit).all()
        return [{"agent_id": r.agent_id, "timestamp": r.timestamp, "value": r.value,
                 "tags": json.loads(r.tags) if r.tags else {}} for r in rows]

    return app

app = create_app()

@click.command()
@click.option('--host', default='0.0.0.0', help='Host to bind')
@click.option('--port', default=8000, help='Port to bind')
@click.option('--log-file', default='core.log', help='Log file path')
@click.option('--log-level', default='INFO', help='Log level (DEBUG, INFO, WARNING, ERROR)')
def main(host, port, log_file, log_level):
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s %(levelname)s:%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    global logger
    logger = logging.getLogger(__name__)
    logger.info(f"Starting core on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()