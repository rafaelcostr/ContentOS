"""SLO snapshot builder — gateway orchestration (V5.5.3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from contentos_gateway.services.metrics_collector import (
    collect_celery_queues,
    collect_postgres_metrics,
    collect_redis_metrics,
)
from contentos_intelligence.application.slo import evaluate_slos
from contentos_intelligence.domain.slo import SloInfraSnapshot, SloReport
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def _count_pipeline_outcomes_24h(db: AsyncSession) -> tuple[int, int]:
    from contentos_database.models import Pipeline, PipelineStatus

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    completed = await db.scalar(
        select(func.count())
        .select_from(Pipeline)
        .where(Pipeline.status == PipelineStatus.COMPLETED, Pipeline.updated_at >= since)
    )
    failed = await db.scalar(
        select(func.count())
        .select_from(Pipeline)
        .where(Pipeline.status == PipelineStatus.FAILED, Pipeline.updated_at >= since)
    )
    return int(completed or 0), int(failed or 0)


async def _count_job_outcomes_24h(db: AsyncSession) -> tuple[int, int]:
    from contentos_database.models import Job, JobStatus

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    completed = await db.scalar(
        select(func.count())
        .select_from(Job)
        .where(Job.status == JobStatus.COMPLETED, Job.finished_at >= since)
    )
    failed = await db.scalar(
        select(func.count())
        .select_from(Job)
        .where(Job.status == JobStatus.FAILED, Job.finished_at >= since)
    )
    return int(completed or 0), int(failed or 0)


async def build_slo_snapshot(db: AsyncSession) -> SloInfraSnapshot:
    redis_m = await collect_redis_metrics()
    postgres_m = await collect_postgres_metrics(db)
    celery_m = await collect_celery_queues()
    pipe_ok, pipe_fail = await _count_pipeline_outcomes_24h(db)
    job_ok, job_fail = await _count_job_outcomes_24h(db)

    return SloInfraSnapshot(
        redis_healthy=redis_m.get("status") == "healthy",
        postgres_healthy=postgres_m.get("status") == "healthy",
        postgres_latency_ms=float(postgres_m.get("latency_ms", 0)) if postgres_m.get("status") == "healthy" else None,
        celery_workers=int(celery_m.get("workers", 0)),
        celery_pending_total=int(celery_m.get("total_pending", 0)),
        pipeline_completed_24h=pipe_ok,
        pipeline_failed_24h=pipe_fail,
        job_completed_24h=job_ok,
        job_failed_24h=job_fail,
    )


async def build_slo_report(db: AsyncSession) -> SloReport:
    snapshot = await build_slo_snapshot(db)
    return evaluate_slos(snapshot)
