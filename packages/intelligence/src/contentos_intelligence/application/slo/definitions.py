"""SLO definitions and thresholds — V5.5.3."""

from __future__ import annotations

import os

from contentos_intelligence.domain.slo import SloDefinition


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def slo_postgres_latency_warning_ms() -> float:
    return _float_env("SLO_POSTGRES_LATENCY_WARNING_MS", 300.0)


def slo_postgres_latency_critical_ms() -> float:
    return _float_env("SLO_POSTGRES_LATENCY_CRITICAL_MS", 500.0)


def slo_queue_backlog_warning() -> int:
    return _int_env("SLO_QUEUE_BACKLOG_WARNING", 50)


def slo_queue_backlog_critical() -> int:
    return _int_env("SLO_QUEUE_BACKLOG_CRITICAL", 150)


def slo_pipeline_success_min_percent() -> float:
    return _float_env("SLO_PIPELINE_SUCCESS_MIN_PERCENT", 95.0)


def slo_job_success_min_percent() -> float:
    return _float_env("SLO_JOB_SUCCESS_MIN_PERCENT", 90.0)


def slo_min_celery_workers() -> int:
    return _int_env("SLO_MIN_CELERY_WORKERS", 1)


SLO_DEFINITIONS: tuple[SloDefinition, ...] = (
    SloDefinition(
        id="redis-availability",
        name="Redis availability",
        description="Celery broker and cache reachable",
        target="healthy",
        runbook_id="redis-down",
        category="infra",
    ),
    SloDefinition(
        id="postgres-availability",
        name="PostgreSQL availability",
        description="Primary database reachable",
        target="healthy",
        runbook_id="postgres-down",
        category="infra",
    ),
    SloDefinition(
        id="postgres-latency",
        name="PostgreSQL latency",
        description="Round-trip SELECT 1 latency",
        target=f"< {slo_postgres_latency_critical_ms():.0f}ms",
        runbook_id="postgres-latency",
        category="infra",
    ),
    SloDefinition(
        id="celery-workers",
        name="Celery workers",
        description="At least one active worker process",
        target=f">= {slo_min_celery_workers()}",
        runbook_id="celery-workers-zero",
        category="workers",
    ),
    SloDefinition(
        id="queue-backlog",
        name="Queue backlog",
        description="Total pending tasks across agent queues",
        target=f"<= {slo_queue_backlog_warning()}",
        runbook_id="queue-backlog",
        category="workers",
    ),
    SloDefinition(
        id="pipeline-success-24h",
        name="Pipeline success (24h)",
        description="Completed vs failed pipelines in rolling 24h window",
        target=f">= {slo_pipeline_success_min_percent():.0f}%",
        runbook_id="pipeline-failures",
        category="production",
    ),
    SloDefinition(
        id="job-success-24h",
        name="Job success (24h)",
        description="Completed vs failed agent jobs in rolling 24h window",
        target=f">= {slo_job_success_min_percent():.0f}%",
        runbook_id="job-failures",
        category="production",
    ),
)
