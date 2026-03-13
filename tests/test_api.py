import pytest
import requests
import time

BASE_URL = "http://localhost:8000"

@pytest.fixture(scope="module")
def core_running():
    """Проверяем, что core доступен перед тестами."""
    try:
        r = requests.get(f"{BASE_URL}/docs")
        assert r.status_code == 200
    except:
        pytest.skip("Core not running")

def test_post_single_metric(core_running):
    """Отправка одной метрики с корректным timestamp."""
    ts = int(time.time())
    payload = {
        "agent_id": "test_agent",
        "timestamp": ts,
        "metrics": {"cpu_usage": 12.3},
        "tags": {
            "hostname": "test_host",
            "ip": "127.0.0.1",
            "os": "linux",
            "version": "1.0"
        }
    }
    r = requests.post(f"{BASE_URL}/api/v1/metrics", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["received"] == 1

def test_post_single_metric_without_timestamp(core_running):
    """Отправка без timestamp – должна вернуть ошибку 422."""
    payload = {
        "agent_id": "test_agent",
        "metrics": {"cpu_usage": 12.3},
        "tags": {
            "hostname": "test_host",
            "ip": "127.0.0.1",
            "os": "linux",
            "version": "1.0"
        }
    }
    r = requests.post(f"{BASE_URL}/api/v1/metrics", json=payload)
    assert r.status_code == 422
    assert "timestamp" in r.text

def test_post_batch_metrics(core_running):
    """Пакетная отправка нескольких метрик с одинаковым набором тегов."""
    ts = int(time.time())
    # Для batch важно, чтобы все метрики имели одинаковый набор тегов
    common_tags = {
        "hostname": "test_host",
        "ip": "127.0.0.1",
        "os": "linux",
        "version": "1.0"
    }
    payload = {
        "batch": [
            {
                "agent_id": "test_agent",
                "timestamp": ts,
                "metrics": {"cpu_usage": 12.3, "mem_usage": 45.6},
                "tags": common_tags
            },
            {
                "agent_id": "test_agent",
                "timestamp": ts,
                "metrics": {"disk_usage": 67.8},
                "tags": common_tags  # те же теги
            }
        ]
    }
    r = requests.post(f"{BASE_URL}/api/v1/metrics/batch", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["received"] == 3

def test_history(core_running):
    """Получение истории метрик."""
    # Сначала отправим метрику, чтобы было что получать
    ts = int(time.time())
    payload = {
        "agent_id": "test_agent",
        "timestamp": ts,
        "metrics": {"cpu_usage": 12.3},
        "tags": {
            "hostname": "test_host",
            "ip": "127.0.0.1",
            "os": "linux",
            "version": "1.0"
        }
    }
    requests.post(f"{BASE_URL}/api/v1/metrics", json=payload)
    time.sleep(1)
    r = requests.get(f"{BASE_URL}/api/v1/history", params={"metric": "cpu_usage", "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "value" in data[0]
        assert "timestamp" in data[0]

def test_agents(core_running):
    """Получение списка агентов."""
    r = requests.get(f"{BASE_URL}/api/v1/agents")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # Проверяем, что наш тестовый агент есть в списке
    assert any(a["agent_id"] == "test_agent" for a in data)