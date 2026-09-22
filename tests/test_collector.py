from app import collector


def test_get_load_average_on_windows():
    result = collector.get_load_average()

    assert set(result.keys()) == {
        "load_1m",
        "load_5m",
        "load_15m",
    }


def test_collect_system_metrics(monkeypatch):
    monkeypatch.setattr(
        collector,
        "get_load_average",
        lambda: {
            "load_1m": 0.1,
            "load_5m": 0.2,
            "load_15m": 0.3,
        },
    )

    metrics = collector.collect_system_metrics()

    assert "timestamp" in metrics
    assert "hostname" in metrics
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "system" in metrics

    assert "percent" in metrics["cpu"]
    assert "logical_cores" in metrics["cpu"]

    assert "total_bytes" in metrics["memory"]
    assert "available_bytes" in metrics["memory"]
    assert "used_bytes" in metrics["memory"]
    assert "percent" in metrics["memory"]

    assert metrics["system"]["load_1m"] == 0.1