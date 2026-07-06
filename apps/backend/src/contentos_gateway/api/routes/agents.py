"""Agent registry with live stats from DB, Redis, and providers."""

from datetime import datetime

from contentos_database.models import Job, JobStatus, LogEntry, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.metrics_collector import (
    agent_model,
    collect_celery_queues,
)
from contentos_shared.agent_catalog import AGENT_CATALOG
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/agents", tags=["Agents"])

AGENTS = AGENT_CATALOG


class AgentLogItem(BaseModel):
    message: str
    level: str
    created_at: datetime


class AgentStatsResponse(BaseModel):
    name: str
    queue: str
    description: str
    status: str
    provider: str
    model: str
    queue_depth: int
    running: int
    completed_total: int
    failed_total: int
    avg_duration_seconds: float | None
    last_execution: datetime | None
    recent_logs: list[AgentLogItem]


async def _job_stats(db: AsyncSession) -> dict[str, dict]:
    result = await db.execute(
        select(
            Job.step,
            func.count().filter(Job.status == JobStatus.COMPLETED).label("completed"),
            func.count().filter(Job.status == JobStatus.FAILED).label("failed"),
            func.count().filter(Job.status == JobStatus.RUNNING).label("running"),
            func.max(Job.finished_at).label("last_execution"),
            func.avg(func.extract("epoch", Job.finished_at) - func.extract("epoch", Job.started_at)).label(
                "avg_duration"
            ),
        ).group_by(Job.step)
    )
    stats: dict[str, dict] = {}
    for row in result.all():
        stats[row.step] = {
            "completed": int(row.completed or 0),
            "failed": int(row.failed or 0),
            "running": int(row.running or 0),
            "last_execution": row.last_execution,
            "avg_duration": float(row.avg_duration) if row.avg_duration else None,
        }
    return stats


async def _recent_logs(db: AsyncSession, agent: str, limit: int = 5) -> list[AgentLogItem]:
    result = await db.execute(
        select(LogEntry).where(LogEntry.agent == agent).order_by(LogEntry.created_at.desc()).limit(limit)
    )
    return [
        AgentLogItem(message=log.message, level=log.level, created_at=log.created_at) for log in result.scalars().all()
    ]


def _agent_status(running: int, queue_depth: int, workers: int) -> str:
    if running > 0:
        return "running"
    if workers > 0:
        return "online"
    if queue_depth > 0:
        return "queued"
    return "idle"


@router.get("", response_model=list[AgentStatsResponse])
async def list_agents(
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[AgentStatsResponse]:
    job_stats = await _job_stats(db)
    celery = await collect_celery_queues()
    queues = celery.get("queues", {})
    workers = celery.get("workers", 0)

    responses: list[AgentStatsResponse] = []
    for agent in AGENTS:
        step = agent["name"]
        stats = job_stats.get(step, {})
        provider, model = agent_model(step)
        q = agent["queue"]
        depth = queues.get(q, 0)
        running = stats.get("running", 0)

        responses.append(
            AgentStatsResponse(
                name=step,
                queue=q,
                description=agent["description"],
                status=_agent_status(running, depth, workers),
                provider=provider,
                model=model,
                queue_depth=depth,
                running=running,
                completed_total=stats.get("completed", 0),
                failed_total=stats.get("failed", 0),
                avg_duration_seconds=stats.get("avg_duration"),
                last_execution=stats.get("last_execution"),
                recent_logs=[],
            )
        )
    return responses


def _build_agent_response(
    agent: dict,
    stats: dict,
    queues: dict,
    workers: int,
    recent_logs: list[AgentLogItem],
) -> AgentStatsResponse:
    step = agent["name"]
    provider, model = agent_model(step)
    q = agent["queue"]
    depth = queues.get(q, 0)
    running = stats.get("running", 0)
    return AgentStatsResponse(
        name=step,
        queue=q,
        description=agent["description"],
        status=_agent_status(running, depth, workers),
        provider=provider,
        model=model,
        queue_depth=depth,
        running=running,
        completed_total=stats.get("completed", 0),
        failed_total=stats.get("failed", 0),
        avg_duration_seconds=stats.get("avg_duration"),
        last_execution=stats.get("last_execution"),
        recent_logs=recent_logs,
    )


@router.get("/{name}", response_model=AgentStatsResponse)
async def get_agent(
    name: str,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> AgentStatsResponse:
    agent_def = next((a for a in AGENTS if a["name"] == name), None)
    if not agent_def:
        raise HTTPException(status_code=404, detail="Agent not found")

    job_stats = await _job_stats(db)
    celery = await collect_celery_queues()
    stats = job_stats.get(name, {})
    recent_logs = await _recent_logs(db, name)
    return _build_agent_response(
        agent_def,
        stats,
        celery.get("queues", {}),
        celery.get("workers", 0),
        recent_logs,
    )
