import time
import json
from fastapi import FastAPI, Request
from fastapi.responses import Response, HTMLResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import uvicorn
from datetime import datetime

from registry import registry
from database import init_db, get_db, save_metric
from models import MetricPayload

app = FastAPI(title="Metrics Collector Core")

# Инициализация БД при старте
init_db()

@app.on_event("startup")
async def startup():
    print("Core started, database initialized.")

# --- Push-эндпоинт для агентов ---
@app.post("/api/v1/metrics")
async def receive_metrics(payload: MetricPayload):
    ts = payload.timestamp or int(time.time())
    for name, value in payload.metrics.items():
        # Сохраняем в БД
        print(f"🔵 Updating {name} = {value}")
        save_metric(payload.agent_id, ts, name, value, payload.tags)
        # Обновляем Prometheus-реестр
        registry.set_gauge(name, value, {**payload.tags, "agent": payload.agent_id})
    print(f"[{datetime.now().isoformat()}] Received {len(payload.metrics)} metrics from {payload.agent_id}")
    return {"status": "ok", "received": len(payload.metrics)}

# --- Pull-эндпоинт для Prometheus ---
@app.get("/metrics")
async def prometheus_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# --- Список агентов ---
@app.get("/api/v1/agents")
async def list_agents():
    with get_db() as conn:
        cursor = conn.execute("SELECT agent_id, last_seen, hostname, ip FROM agents ORDER BY last_seen DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# --- Исторические данные для дашборда ---
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)