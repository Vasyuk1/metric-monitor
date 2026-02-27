import psutil
import requests
import time
import socket
from datetime import datetime

# Конфигурация
CONFIG = {
    "agent_id": socket.gethostname(),
    "server_url": "http://localhost:8000/api/v1/metrics",  # при Docker заменим на http://core:8000
    "interval": 5,
    "tags": {
        "hostname": socket.gethostname(),
        "ip": socket.gethostbyname(socket.gethostname()),
        "os": "windows"
    }
}

def collect_metrics():
    """Сбор системных метрик через psutil."""
    metrics = {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('C:').percent,
        "net_bytes_sent": psutil.net_io_counters().bytes_sent / 1024 / 1024,
        "net_bytes_recv": psutil.net_io_counters().bytes_recv / 1024 / 1024,
        "process_count": len(psutil.pids()),
        "uptime": time.time() - psutil.boot_time()
    }
    return metrics

def send_metrics():
    metrics = collect_metrics()
    payload = {
        "agent_id": CONFIG["agent_id"],
        "timestamp": int(time.time()),
        "metrics": metrics,
        "tags": CONFIG["tags"]
    }
    try:
        response = requests.post(CONFIG["server_url"], json=payload, timeout=2)
        if response.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent {len(metrics)} metrics")
        else:
            print(f"Server error: {response.status_code}")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    print(f"Agent {CONFIG['agent_id']} started, sending to {CONFIG['server_url']}")
    while True:
        send_metrics()
        time.sleep(CONFIG["interval"])