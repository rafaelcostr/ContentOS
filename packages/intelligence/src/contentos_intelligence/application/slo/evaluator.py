"""SLO evaluator — V5.5.3."""

from __future__ import annotations

from datetime import datetime, timezone

from contentos_intelligence.application.slo.definitions import (
    SLO_DEFINITIONS,
    slo_job_success_min_percent,
    slo_min_celery_workers,
    slo_pipeline_success_min_percent,
    slo_postgres_latency_critical_ms,
    slo_postgres_latency_warning_ms,
    slo_queue_backlog_critical,
    slo_queue_backlog_warning,
)
from contentos_intelligence.domain.slo import SloInfraSnapshot, SloReport, SloState, SloStatus


def _rate_percent(success: int, failed: int) -> float | None:
    total = success + failed
    if total == 0:
        return None
    return success / total * 100.0


def evaluate_slos(snapshot: SloInfraSnapshot) -> SloReport:
    items: list[SloStatus] = []
    for definition in SLO_DEFINITIONS:
        items.append(_evaluate_one(definition.id, definition.name, definition.target, definition.runbook_id, snapshot))
    return SloReport(
        items=items,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )


def _evaluate_one(slo_id: str, name: str, target: str, runbook_id: str, s: SloInfraSnapshot) -> SloStatus:
    if slo_id == "redis-availability":
        return _bool_slo(slo_id, name, target, runbook_id, s.redis_healthy, ok_label="healthy", fail_label="unhealthy")
    if slo_id == "postgres-availability":
        return _bool_slo(slo_id, name, target, runbook_id, s.postgres_healthy, ok_label="healthy", fail_label="unhealthy")
    if slo_id == "postgres-latency":
        return _latency_slo(slo_id, name, target, runbook_id, s.postgres_latency_ms)
    if slo_id == "celery-workers":
        return _workers_slo(slo_id, name, target, runbook_id, s.celery_workers)
    if slo_id == "queue-backlog":
        return _backlog_slo(slo_id, name, target, runbook_id, s.celery_pending_total)
    if slo_id == "pipeline-success-24h":
        return _success_rate_slo(
            slo_id,
            name,
            target,
            runbook_id,
            s.pipeline_completed_24h,
            s.pipeline_failed_24h,
            slo_pipeline_success_min_percent(),
        )
    if slo_id == "job-success-24h":
        return _success_rate_slo(
            slo_id,
            name,
            target,
            runbook_id,
            s.job_completed_24h,
            s.job_failed_24h,
            slo_job_success_min_percent(),
        )
    return SloStatus(
        id=slo_id,
        name=name,
        state="unknown",
        target=target,
        current="—",
        runbook_id=runbook_id,
        message="SLO not implemented",
    )


def _bool_slo(
    slo_id: str,
    name: str,
    target: str,
    runbook_id: str,
    healthy: bool | None,
    *,
    ok_label: str,
    fail_label: str,
) -> SloStatus:
    if healthy is None:
        return SloStatus(slo_id, name, "unknown", target, "—", runbook_id, "No measurement")
    current = ok_label if healthy else fail_label
    state: SloState = "ok" if healthy else "critical"
    msg = "" if healthy else f"{name} breach — see runbook {runbook_id}"
    return SloStatus(slo_id, name, state, target, current, runbook_id, msg)


def _latency_slo(slo_id: str, name: str, target: str, runbook_id: str, latency_ms: float | None) -> SloStatus:
    if latency_ms is None:
        return SloStatus(slo_id, name, "unknown", target, "—", runbook_id, "No measurement")
    warn = slo_postgres_latency_warning_ms()
    crit = slo_postgres_latency_critical_ms()
    current = f"{latency_ms:.0f}ms"
    if latency_ms >= crit:
        state: SloState = "critical"
        msg = f"Latency {current} exceeds critical {crit:.0f}ms"
    elif latency_ms >= warn:
        state = "warning"
        msg = f"Latency {current} above warning {warn:.0f}ms"
    else:
        state = "ok"
        msg = ""
    return SloStatus(slo_id, name, state, target, current, runbook_id, msg)


def _workers_slo(slo_id: str, name: str, target: str, runbook_id: str, workers: int) -> SloStatus:
    minimum = slo_min_celery_workers()
    current = str(workers)
    if workers < minimum:
        return SloStatus(
            slo_id,
            name,
            "critical",
            target,
            current,
            runbook_id,
            f"Only {workers} worker(s) — need >= {minimum}",
        )
    return SloStatus(slo_id, name, "ok", target, current, runbook_id)


def _backlog_slo(slo_id: str, name: str, target: str, runbook_id: str, pending: int) -> SloStatus:
    warn = slo_queue_backlog_warning()
    crit = slo_queue_backlog_critical()
    current = str(pending)
    if pending >= crit:
        state: SloState = "critical"
        msg = f"Backlog {pending} tasks (critical >= {crit})"
    elif pending >= warn:
        state = "warning"
        msg = f"Backlog {pending} tasks (warning >= {warn})"
    else:
        state = "ok"
        msg = ""
    return SloStatus(slo_id, name, state, target, current, runbook_id, msg)


def _success_rate_slo(
    slo_id: str,
    name: str,
    target: str,
    runbook_id: str,
    completed: int,
    failed: int,
    min_percent: float,
) -> SloStatus:
    rate = _rate_percent(completed, failed)
    if rate is None:
        return SloStatus(slo_id, name, "ok", target, "no data", runbook_id, "Insufficient samples in 24h")
    current = f"{rate:.1f}%"
    if rate < min_percent:
        return SloStatus(
            slo_id,
            name,
            "critical",
            target,
            current,
            runbook_id,
            f"Success rate {current} below {min_percent:.0f}% ({completed} ok / {failed} fail)",
        )
    if rate < min_percent + 2:
        return SloStatus(
            slo_id,
            name,
            "warning",
            target,
            current,
            runbook_id,
            f"Success rate {current} near threshold {min_percent:.0f}%",
        )
    return SloStatus(slo_id, name, "ok", target, current, runbook_id)


def build_slo_alerts(report: SloReport) -> list[str]:
    alerts: list[str] = []
    for item in report.items:
        if item.state == "critical" and item.message:
            alerts.append(f"[SLO] {item.name}: {item.message}")
        elif item.state == "warning" and item.message:
            alerts.append(f"[SLO ⚠] {item.name}: {item.message}")
    return alerts
