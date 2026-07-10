"""Pipeline schedule API routes (V3 Tier D1)."""

from datetime import datetime
from uuid import UUID

from contentos_database.cron_helpers import InvalidCronError, compute_next_run, validate_cron
from contentos_database.models import PipelineSchedule, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/projects/{project_id}/schedules", tags=["Scheduler"])


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=500)
    cron_expression: str = Field(min_length=1, max_length=120)
    workflow_name: str | None = Field(default=None, max_length=80)
    timezone: str = Field(default="UTC", max_length=64)
    is_active: bool = True
    context_json: dict | None = None


class ScheduleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    topic: str | None = Field(default=None, max_length=500)
    cron_expression: str | None = Field(default=None, max_length=120)
    workflow_name: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None


class ScheduleResponse(BaseModel):
    id: UUID
    project_id: UUID
    org_id: UUID | None
    name: str
    topic: str
    workflow_name: str | None
    cron_expression: str
    timezone: str
    is_active: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_pipeline_id: UUID | None
    last_error: str | None
    context_json: dict | None = None
    created_at: datetime


def _to_response(row: PipelineSchedule) -> ScheduleResponse:
    return ScheduleResponse(
        id=row.id,
        project_id=row.project_id,
        org_id=row.org_id,
        name=row.name,
        topic=row.topic,
        workflow_name=row.workflow_name,
        cron_expression=row.cron_expression,
        timezone=row.timezone,
        is_active=row.is_active,
        last_run_at=row.last_run_at,
        next_run_at=row.next_run_at,
        last_pipeline_id=row.last_pipeline_id,
        last_error=row.last_error,
        context_json=row.context_json,
        created_at=row.created_at,
    )


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ScheduleResponse]:
    await get_accessible_project(db, project_id, user.id)
    result = await db.execute(
        select(PipelineSchedule)
        .where(PipelineSchedule.project_id == project_id)
        .order_by(PipelineSchedule.created_at.desc())
    )
    return [_to_response(row) for row in result.scalars().all()]


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    project_id: UUID,
    body: ScheduleCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> ScheduleResponse:
    project = await get_accessible_project(db, project_id, user.id)
    try:
        cron = validate_cron(body.cron_expression)
        next_run = compute_next_run(cron, body.timezone)
    except InvalidCronError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = PipelineSchedule(
        project_id=project_id,
        org_id=project.org_id,
        name=body.name.strip(),
        topic=body.topic.strip(),
        workflow_name=body.workflow_name,
        cron_expression=cron,
        timezone=body.timezone.strip() or "UTC",
        is_active=body.is_active,
        created_by_user_id=user.id,
        next_run_at=next_run,
        context_json=body.context_json,
    )
    db.add(row)
    await db.flush()
    return _to_response(row)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    project_id: UUID,
    schedule_id: UUID,
    body: ScheduleUpdate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> ScheduleResponse:
    await get_accessible_project(db, project_id, user.id)
    row = await db.get(PipelineSchedule, schedule_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if body.name is not None:
        row.name = body.name.strip()
    if body.topic is not None:
        row.topic = body.topic.strip()
    if body.workflow_name is not None:
        row.workflow_name = body.workflow_name or None
    if body.is_active is not None:
        row.is_active = body.is_active
    if body.timezone is not None:
        row.timezone = body.timezone.strip() or "UTC"
    if body.cron_expression is not None:
        try:
            row.cron_expression = validate_cron(body.cron_expression)
        except InvalidCronError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if body.cron_expression is not None or body.timezone is not None:
        row.next_run_at = compute_next_run(row.cron_expression, row.timezone)

    await db.flush()
    return _to_response(row)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    project_id: UUID,
    schedule_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> None:
    await get_accessible_project(db, project_id, user.id)
    row = await db.get(PipelineSchedule, schedule_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.delete(row)
    await db.flush()
