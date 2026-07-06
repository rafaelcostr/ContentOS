"""Cost Manager API routes."""

from uuid import UUID

from contentos_cost import get_cost_tracker
from contentos_database.models import Project, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import (
    get_accessible_pipeline,
    get_accessible_project,
    project_access_clause,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/costs", tags=["Costs"])


class CostOverviewResponse(BaseModel):
    total_cost_usd: float
    total_tokens_input: int
    total_tokens_output: int
    total_operations: int
    by_provider: dict[str, dict]
    by_agent: dict[str, dict]


class ProjectCostResponse(CostOverviewResponse):
    project_id: str


@router.get("/overview", response_model=CostOverviewResponse)
async def costs_overview(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CostOverviewResponse:
    project_ids = await _user_project_ids(db, user.id)
    data = await get_cost_tracker().overview(db, project_ids)
    return CostOverviewResponse(**data)


@router.get("/projects/{project_id}", response_model=ProjectCostResponse)
async def costs_by_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProjectCostResponse:
    await _verify_project(db, project_id, user.id)
    data = await get_cost_tracker().by_project(db, project_id)
    return ProjectCostResponse(**data)


@router.get("/pipelines/{pipeline_id}")
async def costs_by_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    await _verify_pipeline_access(db, pipeline_id, user.id)
    return await get_cost_tracker().by_pipeline(db, pipeline_id)


async def _user_project_ids(db: AsyncSession, user_id: UUID) -> list[UUID]:
    result = await db.execute(select(Project.id).where(project_access_clause(user_id)))
    return list(result.scalars().all())


async def _verify_project(db: AsyncSession, project_id: UUID, user_id: UUID) -> None:
    await get_accessible_project(db, project_id, user_id)


async def _verify_pipeline_access(db: AsyncSession, pipeline_id: UUID, user_id: UUID) -> None:
    await get_accessible_pipeline(db, pipeline_id, user_id)
