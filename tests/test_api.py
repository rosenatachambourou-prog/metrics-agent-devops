from fastapi.testclient import TestClient

from app.api import app, received_metrics


client = TestClient(app)


def setup_function():
    received_metrics.clear()


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_receive_metrics():
    payload = {
        "agent": "system-metrics-agent",
        "event_type": "system_metrics",
        "data": {
            "timestamp": "2026-09-22T12:00:00+00:00",
            "hostname": "test-host",
            "cpu": {
                "percent": 20.0,
                "logical_cores": 4,
            },
            "memory": {
                "total_bytes": 1000,
                "available_bytes": 500,
                "used_bytes": 500,
                "percent": 50.0,
            },
            "system": {
                "load_1m": None,
                "load_5m": None,
                "load_15m": None,
            },
        },
    }

    response = client.post("/metrics", json=payload)

    assert response.status_code == 201
    assert response.json()["status"] == "received"
    assert response.json()["total_received"] == 1


def test_latest_metrics_without_data():
    response = client.get("/metrics/latest")

    assert response.status_code == 404