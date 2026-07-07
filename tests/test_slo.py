"""Tests for SLO evaluation — V5.5.3."""

from __future__ import annotations

from contentos_intelligence.application.executive.command_center import merge_command_center_alerts
from contentos_intelligence.application.slo import build_slo_alerts, evaluate_slos, get_runbook, list_runbooks
from contentos_intelligence.domain.slo import SloInfraSnapshot


def test_evaluate_slos_all_ok():
    report = evaluate_slos(
        SloInfraSnapshot(
            redis_healthy=True,
            postgres_healthy=True,
            postgres_latency_ms=50.0,
            celery_workers=4,
            celery_pending_total=10,
            pipeline_completed_24h=98,
            pipeline_failed_24h=2,
            job_completed_24h=95,
            job_failed_24h=2,
        )
    )
    assert all(item.state == "ok" for item in report.items)
    assert report.to_dict()["summary"]["critical"] == 0


def test_evaluate_slos_redis_critical():
    report = evaluate_slos(SloInfraSnapshot(redis_healthy=False, postgres_healthy=True))
    redis = next(i for i in report.items if i.id == "redis-availability")
    assert redis.state == "critical"


def test_evaluate_slos_queue_backlog_warning():
    report = evaluate_slos(
        SloInfraSnapshot(
            redis_healthy=True,
            postgres_healthy=True,
            postgres_latency_ms=20.0,
            celery_workers=2,
            celery_pending_total=60,
        )
    )
    backlog = next(i for i in report.items if i.id == "queue-backlog")
    assert backlog.state == "warning"


def test_build_slo_alerts_includes_critical():
    report = evaluate_slos(SloInfraSnapshot(redis_healthy=False))
    alerts = build_slo_alerts(report)
    assert any("[SLO]" in a for a in alerts)


def test_merge_command_center_alerts_dedupes():
    merged = merge_command_center_alerts(["a", "b"], ["b", "c"])
    assert merged == ["a", "b", "c"]


def test_runbook_catalog():
    books = list_runbooks()
    assert len(books) >= 7
    assert get_runbook("redis-down") is not None
    assert get_runbook("missing") is None
