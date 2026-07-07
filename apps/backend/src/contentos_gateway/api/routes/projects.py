import asyncio
from uuid import UUID

import httpx
from contentos_database.billing_credits import (
    InsufficientCreditsError,
    billing_enforced,
    pipeline_credit_cost,
)
from contentos_database.billing_seed import ensure_org_billing
from contentos_database.models import Pipeline, Project, User
from contentos_database.quota_service import QuotaExceededError, assert_can_start_pipeline, quotas_enforced
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.config import settings
from contentos_gateway.schemas import PipelineResponse, ProjectCreate, ProjectResponse
from contentos_gateway.services.billing_service import consume_pipeline_credit, get_org_billing
from contentos_gateway.services.org_service import (
    ORG_HEADER,
    get_accessible_project,
    project_access_clause,
    resolve_org_id,
)
from contentos_intelligence.application.recommendations import build_project_recommendations
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/projects", tags=["Projects"])


class CreatePipelineRequest(BaseModel):
    topic: str
    workflow_name: str | None = None


class ContentRecommendationResponse(BaseModel):
    kind: str
    title: str
    detail: str
    confidence: str
    source: str
    action_href: str = "/factory"


class ContentRecommendationReportResponse(BaseModel):
    project_id: str
    summary: str
    recommendations: list[ContentRecommendationResponse] = Field(default_factory=list)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    x_organization_id: str | None = Header(None, alias=ORG_HEADER),
) -> list[ProjectResponse]:
    org_id = await resolve_org_id(db, user, x_organization_id)
    result = await db.execute(
        select(Project)
        .where(Project.org_id == org_id, project_access_clause(user.id))
        .order_by(Project.created_at.desc())
    )
    return [ProjectResponse.model_validate(p) for p in result.scalars().all()]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
    x_organization_id: str | None = Header(None, alias=ORG_HEADER),
) -> ProjectResponse:
    org_id = body.org_id or await resolve_org_id(db, user, x_organization_id)
    project = Project(owner_id=user.id, org_id=org_id, name=body.name, description=body.description)
    db.add(project)
    await db.flush()
    try:
        from contentos_memory import get_memory_service

        await get_memory_service().ensure_empty(db, project.id)
    except ImportError:
        pass
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    project = await get_accessible_project(db, project_id, user.id)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}/recommendations", response_model=ContentRecommendationReportResponse)
async def get_project_recommendations(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ContentRecommendationReportResponse:
    await get_accessible_project(db, project_id, user.id)
    report = await build_project_recommendations(db, project_id)
    data = report.to_dict()
    return ContentRecommendationReportResponse(
        project_id=data["project_id"],
        summary=data["summary"],
        recommendations=[ContentRecommendationResponse(**item) for item in data["recommendations"]],
    )


@router.get("/{project_id}/pipelines", response_model=list[PipelineResponse])
async def list_pipelines(
    project_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[PipelineResponse]:
    await get_accessible_project(db, project_id, user.id)
    result = await db.execute(
        select(Pipeline)
        .where(Pipeline.project_id == project_id)
        .order_by(Pipeline.created_at.desc())
        .limit(limit)
    )
    return [
        PipelineResponse(
            id=p.id,
            project_id=p.project_id,
            org_id=p.org_id,
            topic=p.topic,
            workflow_name=p.workflow_name,
            status=p.status.value,
            current_step=p.current_step,
            created_at=p.created_at,
        )
        for p in result.scalars().all()
    ]


@router.post("/{project_id}/pipelines", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    project_id: UUID,
    body: CreatePipelineRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> PipelineResponse:
    project = await get_accessible_project(db, project_id, user.id)
    if project.org_id and quotas_enforced():
        try:
            await assert_can_start_pipeline(db, project.org_id)
        except QuotaExceededError as exc:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "quota_exceeded",
                    "kind": exc.kind,
                    "limit": exc.limit,
                    "current": exc.current,
                },
            ) from exc
    if billing_enforced() and project.org_id:
        await ensure_org_billing(db, project.org_id)
        billing = await get_org_billing(db, project.org_id)
        cost = pipeline_credit_cost()
        if billing.credits_balance < cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits: have {billing.credits_balance}, need {cost}",
            )
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.workflow_engine_url}/internal/pipelines",
                json={
                    "project_id": str(project_id),
                    "topic": body.topic,
                    "workflow_name": body.workflow_name,
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Workflow engine unreachable: {exc}",
        ) from exc
    if resp.status_code != 201:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    pipeline_id = UUID(data["id"])

    pipeline = None
    for attempt in range(5):
        result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
        pipeline = result.scalar_one_or_none()
        if pipeline:
            break
        await asyncio.sleep(0.3 * (attempt + 1))

    if not pipeline:
        raise HTTPException(
            status_code=503,
            detail=f"Pipeline {pipeline_id} created by workflow-engine but not visible in database yet",
        )
    if billing_enforced() and project.org_id:
        try:
            await consume_pipeline_credit(db, project.org_id, pipeline_id)
        except InsufficientCreditsError as exc:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits: have {exc.balance}, need {exc.required}",
            ) from exc
    return PipelineResponse(
        id=pipeline.id,
        project_id=pipeline.project_id,
        org_id=pipeline.org_id,
        topic=pipeline.topic,
        workflow_name=pipeline.workflow_name,
        status=pipeline.status.value,
        current_step=pipeline.current_step,
        created_at=pipeline.created_at,
    )
