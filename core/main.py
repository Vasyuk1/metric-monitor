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
from database import init_db, save_metric, AsyncSessionLocal, Agent, Metric
from models import MetricPayload, MetricsBatch
from sqlalchemy import select

logger = logging.getLogger(__name__)

def create_app():
    app = FastAPI(title="Metrics Collector Core")

    @app.on_event("startup")
    async def startup():
        await init_db()
        logger.info("Core started, database initialized.")

    @app.post("/api/v1/metrics")
    async def receive_metrics(payload: MetricPayload):
        ts = payload.timestamp
        for name, value in payload.metrics.items():
            await save_metric(payload.agent_id, ts, name, value, payload.tags)
            registry.set_gauge(name, value, {**payload.tags, "agent": payload.agent_id})
        logger.info(f"Received {len(payload.metrics)} metrics from {payload.agent_id}")
        return {"status": "ok", "received": len(payload.metrics)}

    @app.post("/api/v1/metrics/batch")
    async def receive_metrics_batch(batch: MetricsBatch):
        total = 0
        for payload in batch.batch:
            ts = payload.timestamp
            for name, value in payload.metrics.items():
                await save_metric(payload.agent_id, ts, name, value, payload.tags)
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
                        await save_metric(payload.agent_id, ts, name, value, payload.tags)
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
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Agent.agent_id, Agent.last_seen, Agent.hostname, Agent.ip)
                .order_by(Agent.last_seen.desc())
            )
            rows = result.all()
            return [{"agent_id": r[0], "last_seen": r[1], "hostname": r[2], "ip": r[3]} for r in rows]

    @app.get("/api/v1/history")
    async def get_history(metric: str, from_ts: int = None, to_ts: int = None, limit: int = 1000):
        async with AsyncSessionLocal() as session:
            query = select(Metric.agent_id, Metric.timestamp, Metric.value, Metric.tags) \
                .where(Metric.name == metric)
            if from_ts:
                query = query.where(Metric.timestamp >= from_ts)
            if to_ts:
                query = query.where(Metric.timestamp <= to_ts)
            query = query.order_by(Metric.timestamp.desc()).limit(limit)
            result = await session.execute(query)
            rows = result.all()
            return [{"agent_id": r[0], "timestamp": r[1], "value": r[2],
                     "tags": json.loads(r[3]) if r[3] else {}} for r in rows]

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