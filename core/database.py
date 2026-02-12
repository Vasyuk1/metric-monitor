import sqlite3
import json
from contextlib import contextmanager

DATABASE = "metrics.db"

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                hostname TEXT,
                ip TEXT,
                first_seen INTEGER NOT NULL,
                last_seen INTEGER NOT NULL,
                tags TEXT
            );
            
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp INTEGER NOT NULL,
                tags TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_metrics_agent_time ON metrics(agent_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_metrics_name_time ON metrics(name, timestamp);
            
            CREATE VIEW IF NOT EXISTS latest_metrics AS
            SELECT m.agent_id, m.name, m.value, m.timestamp
            FROM metrics m
            INNER JOIN (
                SELECT agent_id, name, MAX(timestamp) as max_ts
                FROM metrics
                GROUP BY agent_id, name
            ) latest ON m.agent_id = latest.agent_id AND m.name = latest.name AND m.timestamp = latest.max_ts;
        """)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def save_metric(agent_id: str, timestamp: int, name: str, value: float, tags: dict = None):
    with get_db() as conn:
        cursor = conn.cursor()
        # Обновить информацию об агенте
        cursor.execute("""
            INSERT INTO agents (agent_id, hostname, ip, first_seen, last_seen, tags)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                last_seen = excluded.last_seen,
                hostname = excluded.hostname,
                ip = excluded.ip,
                tags = excluded.tags
        """, (agent_id, 
              tags.get('hostname') if tags else None,
              tags.get('ip') if tags else None,
              timestamp, timestamp, 
              json.dumps(tags) if tags else None))
        # Сохранить метрику
        cursor.execute("""
            INSERT INTO metrics (agent_id, name, value, timestamp, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, name, value, timestamp, json.dumps(tags) if tags else None))
        conn.commit()