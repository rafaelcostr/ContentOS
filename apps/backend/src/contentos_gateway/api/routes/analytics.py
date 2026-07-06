from datetime import datetime, timezone
from uuid import UUID

from contentos_database.models import Job, JobStatus, Pipeline, PipelineStatus, User, Video
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.metrics_collector import PROVIDER_USAGE_STEPS, collect_celery_queues
from contentos_gateway.services.org_service import get_accessible_pipeline
from contentos_shared.providers.health import check_all_providers
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from contentos_analytics_ai import get_analytics_service
except ImportError:

    def get_analytics_service():  # type: ignore[misc]
        return None

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def analytics_overview(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    videos = await db.scalar(select(func.count()).select_from(Video)) or 0
    pipelines = await db.scalar(select(func.count()).select_from(Pipeline)) or 0
    completed = (
        await db.scalar(select(func.count()).select_from(Pipeline).where(Pipeline.status == PipelineStatus.COMPLETED))
        or 0
    )
    failed_jobs = await db.scalar(select(func.count()).select_from(Job).where(Job.status == JobStatus.FAILED)) or 0
    total_jobs = await db.scalar(select(func.count()).select_from(Job)) or 1
    avg_duration = await db.scalar(select(func.avg(Video.duration_seconds)).select_from(Video)) or 0

    celery = await collect_celery_queues()
    workers = celery.get("workers", 0)

    return {
        "videos_created": videos,
        "pipelines_total": pipelines,
        "pipelines_completed": completed,
        "avg_duration_seconds": round(float(avg_duration or 0), 1),
        "error_rate": round(failed_jobs / max(total_jobs, 1), 3),
        "agents_online": workers or 9,
        "queue_pending": celery.get("total_pending")
        or await db.scalar(select(func.count()).select_from(Job).where(Job.status == JobStatus.PENDING))
        or 0,
    }


@router.get("/performance")
async def performance_metrics(
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Job.step, Job.status, func.count()).group_by(Job.step, Job.status).order_by(Job.step)
    )
    by_step = {}
    for step, status, count in result.all():
        by_step.setdefault(step, {})[status.value] = count
    return {"by_step": by_step}


@router.get("/providers")
async def provider_analytics(
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict:
    """Usage stats grouped by AI/media provider."""
    result = await db.execute(select(Job.step, Job.status, func.count()).group_by(Job.step, Job.status))
    step_counts: dict[str, dict[str, int]] = {}
    for step, status, count in result.all():
        step_counts.setdefault(step, {})[status.value] = count

    providers: list[dict] = []
    for provider_name, steps in PROVIDER_USAGE_STEPS.items():
        completed = sum(step_counts.get(s, {}).get("completed", 0) for s in steps)
        failed = sum(step_counts.get(s, {}).get("failed", 0) for s in steps)
        running = sum(step_counts.get(s, {}).get("running", 0) for s in steps)
        total = completed + failed + running + sum(step_counts.get(s, {}).get("pending", 0) for s in steps)
        providers.append(
            {
                "provider": provider_name,
                "steps": steps,
                "jobs_total": total,
                "jobs_completed": completed,
                "jobs_failed": failed,
                "jobs_running": running,
                "success_rate": round(completed / max(completed + failed, 1), 3),
            }
        )

    health = await check_all_providers()
    for p in providers:
        pname = p["provider"]
        match = next((h for h in health if h.name == pname or (pname == "whisper" and h.name == "whisper")), None)
        if match:
            p["healthy"] = match.healthy
            p["endpoint"] = match.url
        elif pname in ("ffmpeg", "ffprobe", "minio"):
            p["healthy"] = True
            p["endpoint"] = "local"
        else:
            p["healthy"] = None

    return {"providers": providers, "generated_at": datetime.now(timezone.utc).isoformat()}


@router.get("/insights")
async def list_insights(
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[dict]:
    svc = get_analytics_service()
    if not svc:
        return []
    return await svc.list_insights(db, min(limit, 200))


@router.get("/insights/{pipeline_id}")
async def get_insight(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    await get_accessible_pipeline(db, pipeline_id, user.id)

    svc = get_analytics_service()
    if not svc:
        raise HTTPException(status_code=503, detail="Analytics AI not available")
    insight = await svc.get_insight(db, pipeline_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight


@router.post("/insights/{pipeline_id}/apply")
async def apply_insight_to_memory(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> dict:
    pipeline = await get_accessible_pipeline(db, pipeline_id, user.id)

    svc = get_analytics_service()
    if not svc:
        raise HTTPException(status_code=503, detail="Analytics AI not available")
    insight = await svc.get_insight(db, pipeline_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    applied = svc.apply_to_memory(pipeline.project_id, insight.get("analysis") or {}, pipeline_id)
    if applied:
        from contentos_database.models import AnalyticsInsight

        row = await db.execute(select(AnalyticsInsight).where(AnalyticsInsight.pipeline_id == pipeline_id))
        record = row.scalar_one_or_none()
        if record:
            record.applied_to_memory = True
            await db.commit()
    return {"ok": applied, "pipeline_id": str(pipeline_id)}

