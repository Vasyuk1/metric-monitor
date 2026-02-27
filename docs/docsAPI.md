# Metrics Collector API

## Базовый URL
`http://localhost:8000/api/v1`

## 1. Отправка метрики (Push)
**POST** `/metrics`

**Тело запроса (JSON):**
```json
{
  "agent_id": "string",
  "timestamp": 1234567890,
  "metrics": {
    "cpu_usage": 12.5,
    "memory_usage": 45.2,
    "disk_usage": 67.8,
    "custom_metric": 42.0
  },
  "tags": {
    "host": "server-01",
    "os": "windows",
    "environment": "prod"
  }
}