# Metrics Collector API

Базовый URL: `http://localhost:8000`

## Эндпоинты

### 1. Отправка одной метрики
`POST /api/v1/metrics`

**Тело запроса (JSON):**
```json
{
  "agent_id": "string",
  "timestamp": 1234567890,
  "metrics": {
    "metric_name": 12.34,
    "another_metric": 56.78
  },
  "tags": {
    "hostname": "server-01",
    "os": "windows",
    "version": "1.0"
  }
}