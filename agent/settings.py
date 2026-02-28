import os
import socket
from typing import Dict, Any

class Settings:
    # Основные настройки
    AGENT_ID: str = os.getenv("AGENT_ID", socket.gethostname())
    SERVER_URL: str = os.getenv("SERVER_URL", "http://localhost:8000/api/v1/metrics/batch")
    INTERVAL: int = int(os.getenv("INTERVAL", 5))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", 10))  # сколько метрик копить перед отправкой
    LOG_FILE: str = os.getenv("LOG_FILE", "agent.log")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    VERSION: str = "1.0"
    
    # Статические теги
    TAGS: Dict[str, str] = {
        "hostname": socket.gethostname(),
        "ip": socket.gethostbyname(socket.gethostname()),
        "os": "windows"
    }
    
    # Кастомные метрики через переменную окружения
    _custom_metrics_str: str = os.getenv("CUSTOM_METRICS", "")
    CUSTOM_METRICS: Dict[str, float] = {}
    if _custom_metrics_str:
        for pair in _custom_metrics_str.split(","):
            if ":" in pair:
                k, v = pair.split(":", 1)
                try:
                    CUSTOM_METRICS[k.strip()] = float(v.strip())
                except ValueError:
                    pass

settings = Settings()