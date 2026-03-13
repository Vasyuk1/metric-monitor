import os
import socket
from typing import Dict, Any, List

class Settings:
    # Основные настройки
    AGENT_ID: str = os.getenv("AGENT_ID", socket.gethostname())
    SERVER_URL: str = os.getenv("SERVER_URL", "http://localhost:8000/api/v1/metrics/batch")
    INTERVAL: int = int(os.getenv("INTERVAL", 5))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", 10))
    
    # Логирование
    LOG_FILE: str = os.getenv("LOG_FILE", "agent.log")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Версия протокола
    VERSION: str = os.getenv("VERSION", "1.0")
    
    # Статические теги
    TAGS: Dict[str, str] = {
        "hostname": socket.gethostname(),
        "ip": socket.gethostbyname(socket.gethostname()),
        "os": "windows",
        "version": VERSION
    }
    
    # Кастомные метрики через переменную окружения
    CUSTOM_METRICS: Dict[str, float] = {}
    
    @classmethod
    def parse_custom_metrics(cls, env_var: str) -> Dict[str, float]:
        """Парсит строку вида 'metric1:12.3,metric2:45.6' в словарь."""
        metrics = {}
        if not env_var:
            return metrics
        for pair in env_var.split(","):
            if ":" in pair:
                key, val = pair.split(":", 1)
                try:
                    metrics[key.strip()] = float(val.strip())
                except ValueError:
                    pass  # игнорируем некорректные значения
        return metrics

# Инициализация кастомных метрик из переменной окружения
custom_metrics_str = os.getenv("CUSTOM_METRICS", "")
Settings.CUSTOM_METRICS = Settings.parse_custom_metrics(custom_metrics_str)

settings = Settings()