import psutil
import requests
import time
import logging
from datetime import datetime
from typing import Dict, List, Any

from settings import settings

# Настройка логирования
logging.basicConfig(
    filename=settings.LOG_FILE,
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s %(levelname)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Дублирование в консоль
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s', datefmt='%H:%M:%S')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)

def collect_metrics() -> Dict[str, float]:
    """Сбор системных метрик."""
    metrics = {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('C:').percent,
        "net_bytes_sent": psutil.net_io_counters().bytes_sent / 1024 / 1024,
        "net_bytes_recv": psutil.net_io_counters().bytes_recv / 1024 / 1024,
        "process_count": len(psutil.pids()),
        "uptime": time.time() - psutil.boot_time()
    }
    metrics.update(settings.CUSTOM_METRICS)
    return metrics

def build_payload(metrics: Dict[str, float], batch: List[Dict[str, Any]]) -> None:
    """Добавляет метрики в текущий батч."""
    payload = {
        "agent_id": settings.AGENT_ID,
        "timestamp": int(time.time()),
        "metrics": metrics,
        "tags": settings.TAGS.copy()
    }
    payload["tags"]["version"] = settings.VERSION
    batch.append(payload)

def send_batch(batch: List[Dict[str, Any]]) -> None:
    """Отправляет накопленный батч на сервер."""
    if not batch:
        return
    try:
        response = requests.post(
            settings.SERVER_URL,
            json={"batch": batch},
            timeout=5
        )
        if response.status_code == 200:
            total_metrics = sum(len(p['metrics']) for p in batch)
            logger.info(f"Sent batch of {len(batch)} payloads, {total_metrics} metrics")
        elif response.status_code >= 500:
            logger.error(f"Server error {response.status_code}: {response.text}")
        else:
            logger.warning(f"Unexpected response {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError:
        logger.error("Connection error: server unreachable")
    except Exception as e:
        logger.exception(f"Unexpected error sending batch: {e}")

def main():
    logger.info(f"Agent {settings.AGENT_ID} started. Sending to {settings.SERVER_URL} every {settings.INTERVAL}s")
    batch = []
    last_send = time.time()
    
    while True:
        try:
            metrics = collect_metrics()
            build_payload(metrics, batch)
            
            if len(batch) >= settings.BATCH_SIZE or (time.time() - last_send) >= settings.INTERVAL:
                send_batch(batch)
                batch.clear()
                last_send = time.time()
            
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
            break
        except Exception as e:
            logger.exception("Unhandled error in main loop")
            time.sleep(5)

if __name__ == "__main__":
    main()