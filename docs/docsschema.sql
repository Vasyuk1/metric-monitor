
---

### **`docs/schema.sql`**
```sql
-- Таблица агентов
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    hostname TEXT,
    ip TEXT,
    first_seen INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    tags TEXT  -- JSON
);

-- Таблица метрик (временные ряды)
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL REFERENCES agents(agent_id),
    name TEXT NOT NULL,          -- например, 'cpu_usage'
    value REAL NOT NULL,
    timestamp INTEGER NOT NULL,
    tags TEXT,                  -- JSON с дополнительными метками
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- Индексы для быстрых запросов
CREATE INDEX idx_metrics_agent_time ON metrics(agent_id, timestamp);
CREATE INDEX idx_metrics_name_time ON metrics(name, timestamp);

-- Представление для последних значений (для Prometheus)
CREATE VIEW latest_metrics AS
SELECT m.agent_id, m.name, m.value, m.timestamp
FROM metrics m
INNER JOIN (
    SELECT agent_id, name, MAX(timestamp) as max_ts
    FROM metrics
    GROUP BY agent_id, name
) latest ON m.agent_id = latest.agent_id AND m.name = latest.name AND m.timestamp = latest.max_ts;