-- Схема базы данных для системы сбора метрик
-- Версия: 1.0

PRAGMA foreign_keys = ON;  -- обязательно включить поддержку внешних ключей

-- Таблица агентов (источников метрик)
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,        -- уникальный идентификатор агента (например, hostname)
    hostname TEXT,                    -- имя хоста
    ip TEXT,                          -- IP-адрес (если известен)
    port INTEGER,                     -- порт для управления (если агент слушает)
    first_seen INTEGER NOT NULL,      -- timestamp первого появления
    last_seen INTEGER NOT NULL,       -- timestamp последней активности
    tags TEXT,                        -- JSON с дополнительными метками агента
                                      -- пример: {"os":"windows","environment":"prod","region":"ru"}
    version TEXT                       -- версия протокола агента
);

-- Таблица метрик (временные ряды)
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,            -- ссылка на агента
    name TEXT NOT NULL,                -- имя метрики (рекомендуется иерархический формат)
                                       -- пример: "system/cpu/usage", "app/requests/count"
    value REAL NOT NULL,               -- числовое значение
    timestamp INTEGER NOT NULL,        -- время сбора (Unix timestamp)
    tags TEXT,                         -- JSON с метками, специфичными для данной метрики
                                       -- пример: {"disk":"C:","mount":"/"}
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

-- Индексы для быстрых запросов
CREATE INDEX idx_metrics_agent_time ON metrics(agent_id, timestamp);
CREATE INDEX idx_metrics_name_time ON metrics(name, timestamp);

-- Представление для последних значений метрик (для Prometheus-подобных запросов)
CREATE VIEW latest_metrics AS
SELECT m.agent_id, m.name, m.value, m.timestamp
FROM metrics m
INNER JOIN (
    SELECT agent_id, name, MAX(timestamp) as max_ts
    FROM metrics
    GROUP BY agent_id, name
) latest ON m.agent_id = latest.agent_id AND m.name = latest.name AND m.timestamp = latest.max_ts;