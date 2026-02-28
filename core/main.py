import time
import json
import logging
import click
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import uvicorn
from datetime import datetime

from registry import registry
from database import init_db, get_db, save_metric
from models import MetricPayload, MetricsBatch

# Настройка логирования будет производиться в функции main
logger = logging.getLogger(__name__)

def create_app():
    app = FastAPI(title="Metrics Collector Core")

    @app.on_event("startup")
    async def startup():
        init_db()
        logger.info("Core started, database initialized.")

    @app.post("/api/v1/metrics")
    async def receive_metrics(payload: MetricPayload):
        ts = payload.timestamp or int(time.time())
        for name, value in payload.metrics.items():
            save_metric(payload.agent_id, ts, name, value, payload.tags)
            registry.set_gauge(name, value, {**payload.tags, "agent": payload.agent_id})
        logger.info(f"Received {len(payload.metrics)} metrics from {payload.agent_id}")
        return {"status": "ok", "received": len(payload.metrics)}

    @app.post("/api/v1/metrics/batch")
    async def receive_metrics_batch(batch: MetricsBatch):
        total = 0
        metrics_to_insert = []
        agent_updates = {}

        for payload in batch.batch:
            ts = payload.timestamp or int(time.time())
            # Обновление информации об агенте
            if payload.agent_id not in agent_updates:
                agent_updates[payload.agent_id] = {
                    "hostname": payload.tags.get("hostname") if payload.tags else None,
                    "ip": payload.tags.get("ip") if payload.tags else None,
                    "last_seen": ts,
                    "first_seen": ts,
                    "tags": json.dumps(payload.tags) if payload.tags else None
                }
            else:
                agent_updates[payload.agent_id]["last_seen"] = max(agent_updates[payload.agent_id]["last_seen"], ts)

            for name, value in payload.metrics.items():
                metrics_to_insert.append((
                    payload.agent_id,
                    name,
                    value,
                    ts,
                    json.dumps(payload.tags) if payload.tags else None
                ))
                total += 1
                registry.set_gauge(name, value, {**payload.tags, "agent": payload.agent_id})

        with get_db() as conn:
            cursor = conn.cursor()
            for agent_id, data in agent_updates.items():
                cursor.execute("""
                    INSERT INTO agents (agent_id, hostname, ip, first_seen, last_seen, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(agent_id) DO UPDATE SET
                        last_seen = excluded.last_seen,
                        hostname = excluded.hostname,
                        ip = excluded.ip,
                        tags = excluded.tags
                """, (agent_id, data["hostname"], data["ip"], data["first_seen"], data["last_seen"], data["tags"]))

            cursor.executemany("""
                INSERT INTO metrics (agent_id, name, value, timestamp, tags)
                VALUES (?, ?, ?, ?, ?)
            """, metrics_to_insert)
            conn.commit()

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
                    ts = payload.timestamp or int(time.time())
                    for name, value in payload.metrics.items():
                        save_metric(payload.agent_id, ts, name, value, payload.tags)
                        registry.set_gauge(name, value, {**payload.tags, "agent": payload.agent_id})
                    await websocket.send_text("ok")
                except Exception as e:
                    await websocket.send_text(f"error: {str(e)}")
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")

    @app.get("/metrics")
    async def prometheus_metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/v1/agents")
    async def list_agents():
        with get_db() as conn:
            cursor = conn.execute("SELECT agent_id, last_seen, hostname, ip FROM agents ORDER BY last_seen DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    @app.get("/api/v1/history")
    async def get_history(metric: str, from_ts: int = None, to_ts: int = None, limit: int = 1000):
        with get_db() as conn:
            query = "SELECT agent_id, timestamp, value, tags FROM metrics WHERE name = ?"
            params = [metric]
            if from_ts:
                query += " AND timestamp >= ?"
                params.append(from_ts)
            if to_ts:
                query += " AND timestamp <= ?"
                params.append(to_ts)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [{"agent_id": r[0], "timestamp": r[1], "value": r[2], "tags": json.loads(r[3]) if r[3] else {}} for r in rows]

    return app

@click.command()
@click.option('--host', default='0.0.0.0', help='Host to bind')
@click.option('--port', default=8000, help='Port to bind')
@click.option('--log-file', default='core.log', help='Log file path')
@click.option('--log-level', default='INFO', help='Log level (DEBUG, INFO, WARNING, ERROR)')
def main(host, port, log_file, log_level):
    # Настройка логирования
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

    app = create_app()
    logger.info(f"Starting core on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()