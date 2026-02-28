import requests

url = "http://localhost:8000/api/v1/metrics/batch"
payload = {
    "batch": [
        {
            "agent_id": "test_agent",
            "timestamp": 1700000000,
            "metrics": {
                "cpu_usage": 12.3,
                "memory_usage": 45.6,
                "disk_usage": 67.8
            },
            "tags": {
                "os": "windows",
                "hostname": "test-pc"
            }
        }
    ]
}

response = requests.post(url, json=payload)
print("Status code:", response.status_code)
print("Response:", response.json())