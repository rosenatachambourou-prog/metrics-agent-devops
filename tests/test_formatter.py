import pytest

from app.formatter import format_metrics


def sample_metrics():
    return {
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
            "load_1m": 0.1,
            "load_5m": 0.2,
            "load_15m": 0.3,
        },
    }


def test_format_metrics():
    result = format_metrics(sample_metrics())

    assert result["agent"] == "system-metrics-agent"
    assert result["event_type"] == "system_metrics"
    assert result["data"] == sample_metrics()


def test_format_metrics_custom_agent():
    result = format_metrics(
        sample_metrics(),
        agent_name="agent-test",
    )

    assert result["agent"] == "agent-test"


def test_format_metrics_missing_key():
    metrics = sample_metrics()
    del metrics["cpu"]

    with pytest.raises(ValueError):
        format_metrics(metrics)