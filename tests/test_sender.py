import pytest
import requests

from app.sender import MetricsDeliveryError, send_metrics


class FakeResponse:
    status_code = 201
    text = '{"status":"received"}'

    def raise_for_status(self):
        return None

    def json(self):
        return {"status": "received"}


def test_send_metrics_success(monkeypatch):
    def fake_post(endpoint, json, timeout):
        assert endpoint == "http://example.test/metrics"
        assert json == {"agent": "test"}
        assert timeout == 5
        return FakeResponse()

    monkeypatch.setattr(
        "app.sender.requests.post",
        fake_post,
    )

    result = send_metrics(
        "http://example.test/metrics",
        {"agent": "test"},
    )

    assert result["status_code"] == 201
    assert result["response"] == {"status": "received"}


def test_send_metrics_connection_error(monkeypatch):
    def fake_post(endpoint, json, timeout):
        raise requests.ConnectionError("connexion impossible")

    monkeypatch.setattr(
        "app.sender.requests.post",
        fake_post,
    )

    with pytest.raises(MetricsDeliveryError):
        send_metrics(
            "http://example.test/metrics",
            {"agent": "test"},
        )