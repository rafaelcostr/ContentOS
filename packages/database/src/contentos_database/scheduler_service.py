"""Pipeline schedule runner (V3 Tier D1)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID

import httpx
from contentos_database.cron_helpers import compute_next_run, render_topic_template
from contentos_database.models import PipelineSchedule
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def scheduler_enabled() -> bool:
    return os.getenv("SCHEDULER_ENABLED", "true").lower() in ("1", "true", "yes")


def scheduler_interval_seconds() -> int:
    try:
        return max(15, int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "60")))
    except ValueError:
        return 60


async def refresh_next_run(schedule: PipelineSchedule, *, base: datetime | None = None) -> None:
    schedule.next_run_at = compute_next_run(schedule.cron_expression, schedule.timezone, base=base)
    schedule.updated_at = datetime.now(timezone.utc)


async def run_due_schedules(db: AsyncSession, workflow_engine_url: str) -> list[UUID]:
    """Trigger pipelines for schedules whose next_run_at has passed."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PipelineSchedule).where(
            PipelineSchedule.is_active.is_(True),
            PipelineSchedule.next_run_at.is_not(None),
            PipelineSchedule.next_run_at <= now,
        )
    )
    triggered: list[UUID] = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        for schedule in result.scalars().all():
            topic = render_topic_template(schedule.topic, when=now)
            payload: dict = {
                "project_id": str(schedule.project_id),
                "topic": topic,
                "workflow_name": schedule.workflow_name,
                "auto_start": True,
            }
            if schedule.context_json:
                payload["context_json"] = schedule.context_json
            try:
                resp = await client.post(
                    f"{workflow_engine_url.rstrip('/')}/internal/pipelines",
                    json=payload,
                )
            except httpx.HTTPError as exc:
                schedule.last_error = str(exc)[:500]
                await refresh_next_run(schedule, base=now)
                continue

            if resp.status_code == 201:
                data = resp.json()
                schedule.last_run_at = now
                schedule.last_pipeline_id = UUID(data["id"])
                schedule.last_error = None
                triggered.append(schedule.id)
            else:
                schedule.last_error = resp.text[:500]
            await refresh_next_run(schedule, base=now)
    return triggered
