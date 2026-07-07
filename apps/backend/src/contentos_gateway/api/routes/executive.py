"""Executive Dashboard API — Epic 12 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_gateway.services.slo_service import build_slo_report
from contentos_intelligence.application.executive import ExecutiveSummaryService
from contentos_intelligence.application.executive.command_center import merge_command_center_alerts
from contentos_intelligence.application.slo import build_slo_alerts
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


class SloStatusResponse(BaseModel):
    id: str
    name: str
    state: str
    target: str
    current: str
    runbook_id: str
    message: str = ""


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
    factory_batches_total: int = 0
    factory_batches_running: int = 0
    factory_pending_approval: int = 0
    platform_snapshots: int = 0
    performance_insights: int = 0
    comment_insights: int = 0
    community_drafts_pending: int = 0
    oauth_channels_connected: int = 0
    alerts: list[str] = Field(default_factory=list)
    slo_items: list[SloStatusResponse] = Field(default_factory=list)
    v5_modules: list[ModuleStatusResponse] = Field(default_factory=list)


@router.get("/summary", response_model=ExecutiveSummaryResponse)
async def get_executive_summary(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> ExecutiveSummaryResponse:

    project = await get_accessible_project(db, project_id, user.id)
    summary = await ExecutiveSummaryService().build(db, project_id, project_name=project.name)
    slo_report = await build_slo_report(db)
    slo_alerts = build_slo_alerts(slo_report)
    d = summary.to_dict()
    d["alerts"] = merge_command_center_alerts(d.get("alerts", []), slo_alerts)
    d["slo_items"] = slo_report.to_dict()["items"]
    return ExecutiveSummaryResponse(
        **{k: v for k, v in d.items() if k not in ("modules", "v5_modules", "slo_items")},
        modules=[ModuleStatusResponse(**m) for m in d["modules"]],
        v5_modules=[ModuleStatusResponse(**m) for m in d.get("v5_modules", [])],
        slo_items=[SloStatusResponse(**s) for s in d.get("slo_items", [])],
    )
