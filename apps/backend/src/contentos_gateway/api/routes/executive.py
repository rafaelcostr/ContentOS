"""Executive Dashboard API — Epic 12 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.executive import ExecutiveSummaryService
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/executive", tags=["Executive Dashboard"])


class ModuleStatusResponse(BaseModel):
    key: str
    label: str
    status: str
    metric: str
    href: str
    detail: str = ""


class ExecutiveSummaryResponse(BaseModel):
    project_id: str
    project_name: str
    pipelines_total: int
    pipelines_completed: int
    knowledge_entries: int
    learning_insights: int
    graph_nodes: int
    graph_edges: int
    ab_variant_sets: int
    specialists_available: int
    avg_content_score: float | None = None
    avg_viral_score: float | None = None
    latest_trend_score: float | None = None
    latest_trend_growth: str | None = None
    dna_preview: str = ""
    hook_patterns: list[str] = Field(default_factory=list)
    latest_learning_topic: str | None = None
    modules: list[ModuleStatusResponse]


@router.get("/summary", response_model=ExecutiveSummaryResponse)
async def get_executive_summary(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> ExecutiveSummaryResponse:

    project = await get_accessible_project(db, project_id, user.id)
    summary = await ExecutiveSummaryService().build(db, project_id, project_name=project.name)
    d = summary.to_dict()
    return ExecutiveSummaryResponse(
        **{k: v for k, v in d.items() if k != "modules"},
        modules=[ModuleStatusResponse(**m) for m in d["modules"]],
    )
