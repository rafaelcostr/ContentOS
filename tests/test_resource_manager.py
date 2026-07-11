from contentos_autopilot.resources import build_resource_readiness


def test_resource_readiness_ready_when_resources_are_healthy() -> None:
    readiness = build_resource_readiness(
        system_metrics={"cpu": {"percent": 30}, "memory": {"percent": 40}, "disk": {"percent": 50}},
        celery_metrics={"workers": 2, "total_pending": 1},
        quantity=1,
    )

    data = readiness.to_dict()

    assert data["status"] == "ready"
    assert data["execution_window"] == "now"
    assert data["score"] >= 80


def test_resource_readiness_blocks_without_workers_and_high_memory() -> None:
    readiness = build_resource_readiness(
        system_metrics={"cpu": {"percent": 40}, "memory": {"percent": 94}, "disk": {"percent": 60}},
        celery_metrics={"workers": 0, "total_pending": 0},
    )

    assert readiness.status == "blocked"
    assert any("RAM" in blocker for blocker in readiness.blockers)
    assert any("worker" in blocker.lower() for blocker in readiness.blockers)


def test_resource_readiness_defers_for_queue_backlog() -> None:
    readiness = build_resource_readiness(
        system_metrics={"cpu": {"percent": 50}, "memory": {"percent": 50}, "disk": {"percent": 50}},
        celery_metrics={"workers": 1, "total_pending": 50},
        quantity=2,
    )

    assert readiness.status == "defer"
    assert readiness.execution_window in {"soon", "off_peak"}
