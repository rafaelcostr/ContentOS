"""Pipeline routes — list, detail, jobs, cancel, delete."""

from uuid import UUID

import httpx
from contentos_database.models import Pipeline, PipelineStatus, Project, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.config import settings
from contentos_gateway.schemas import PipelineResponse
from contentos_gateway.services.org_service import (
    ORG_HEADER,
    get_accessible_pipeline,
    project_access_clause,
    resolve_org_id,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


async def _cancel_via_workflow(pipeline_id: UUID) -> None:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.workflow_engine_url}/internal/pipelines/{pipeline_id}/cancel"
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Workflow engine unreachable: {exc}") from exc
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)


class JobSummary(BaseModel):
    id: UUID
    step: str
    status: str
    order: int
    error_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class PipelineDetailResponse(PipelineResponse):
    jobs: list[JobSummary]
    error_message: str | None = None


def _pipeline_response(p: Pipeline) -> PipelineResponse:
    return PipelineResponse(
        id=p.id,
        project_id=p.project_id,
        org_id=p.org_id,
        topic=p.topic,
        workflow_name=p.workflow_name,
        status=p.status.value,
        current_step=p.current_step,
        created_at=p.created_at,
    )


@router.get("", response_model=list[PipelineResponse])
async def list_all_pipelines(
    limit: int = 20,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    x_organization_id: str | None = Header(None, alias=ORG_HEADER),
) -> list[PipelineResponse]:
    org_id = await resolve_org_id(db, user, x_organization_id)
    result = await db.execute(
        select(Pipeline)
        .join(Project)
        .where(Pipeline.org_id == org_id, project_access_clause(user.id))
        .order_by(Pipeline.created_at.desc())
        .limit(limit)
    )
    return [_pipeline_response(p) for p in result.scalars().all()]


@router.get("/{pipeline_id}", response_model=PipelineDetailResponse)
async def get_pipeline_detail(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PipelineDetailResponse:
    result = await db.execute(
        select(Pipeline)
        .options(selectinload(Pipeline.jobs))
        .join(Project)
        .where(Pipeline.id == pipeline_id, project_access_clause(user.id))
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    jobs = sorted(pipeline.jobs, key=lambda j: j.order)
    base = _pipeline_response(pipeline)
    return PipelineDetailResponse(
        **base.model_dump(),
        error_message=pipeline.error_message,
        jobs=[
            JobSummary(
                id=j.id,
                step=j.step,
                status=j.status.value,
                order=j.order,
                error_message=j.error_message,
                started_at=j.started_at.isoformat() if j.started_at else None,
                finished_at=j.finished_at.isoformat() if j.finished_at else None,
            )
            for j in jobs
        ],
    )


@router.post("/{pipeline_id}/cancel", response_model=PipelineResponse)
async def cancel_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> PipelineResponse:
    pipeline = await get_accessible_pipeline(db, pipeline_id, user.id)
    if pipeline.status not in (PipelineStatus.RUNNING, PipelineStatus.PENDING):
        raise HTTPException(status_code=400, detail="Pipeline is not running")
    await _cancel_via_workflow(pipeline_id)
    await db.refresh(pipeline)
    return _pipeline_response(pipeline)


@router.delete("/{pipeline_id}", status_code=204, response_class=Response)
async def delete_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> Response:
    pipeline = await get_accessible_pipeline(db, pipeline_id, user.id)
    if pipeline.status in (PipelineStatus.RUNNING, PipelineStatus.PENDING):
        await _cancel_via_workflow(pipeline_id)
        await db.refresh(pipeline)
    await db.delete(pipeline)
    await db.flush()
    return Response(status_code=204)
