"""Trend Forecast API — Epic 10 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.trend_forecast import TrendForecastService
from contentos_intelligence.infrastructure.trend_forecast_repository import (
    TrendForecastRepository,
    count_kb_entries_sync,
    list_learning_insights_sync,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/trend", tags=["Trend Forecast"])

try:
    from contentos_analytics_ai.infrastructure.db_repository import InsightRepository
except ImportError:
    InsightRepository = None  # type: ignore[misc, assignment]

try:
    from contentos_memory.application.memory_service import get_memory_service
except ImportError:

    def get_memory_service():  # type: ignore[misc]
        return None


class TrendForecastRequest(BaseModel):
    project_id: UUID
    topic: str = Field(min_length=1, max_length=2000)
    pipeline_id: UUID | None = None
    niche: str = ""
    persist: bool = False


class TrendForecastResponse(BaseModel):
    project_id: str
    pipeline_id: str | None
    topic: str
    niche: str
    trend_score: float
    expected_growth: str
    production_recommendation: str
    pacing_hint: str
    pattern_count: int
    sources: list[str]
    signals: dict = Field(default_factory=dict)


@router.post("/forecast", response_model=TrendForecastResponse)
async def forecast_trend(
    body: TrendForecastRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> TrendForecastResponse:
    await get_accessible_project(db, body.project_id, user.id)

    memory = None
    memory_svc = get_memory_service()
    if memory_svc:
        memory = memory_svc.get_memory(body.project_id)

    insights: list[dict] = []
    if InsightRepository:
        repo = InsightRepository()
        insights = await repo.list_by_project(db, body.project_id, limit=10)

    learning_rows = list_learning_insights_sync(body.project_id, limit=10)
    kb_count = count_kb_entries_sync(body.project_id)

    report = TrendForecastService().forecast(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        topic=body.topic,
        niche=body.niche,
        memory=memory,
        insights=insights,
        learning_rows=learning_rows,
        kb_entry_count=kb_count,
    )
    if body.persist and body.pipeline_id:
        await TrendForecastRepository().save_report(db, report)
    return _to_response(report)


@router.get("/forecast/pipeline/{pipeline_id}", response_model=TrendForecastResponse)
async def get_trend_forecast_for_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> TrendForecastResponse:
    from contentos_database.models import Pipeline
    from sqlalchemy import select

    pipeline = (await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await get_accessible_project(db, pipeline.project_id, user.id)
    row = await TrendForecastRepository().get_by_pipeline(db, pipeline_id)
    if not row:
        raise HTTPException(status_code=404, detail="Trend forecast not found")
    return TrendForecastResponse(
        project_id=str(row["project_id"]),
        pipeline_id=str(row.get("pipeline_id") or pipeline_id),
        topic=str(row.get("topic") or ""),
        niche=str(row.get("niche") or ""),
        trend_score=float(row.get("trend_score") or 50),
        expected_growth=str(row.get("expected_growth") or "moderate"),
        production_recommendation=str(row.get("production_recommendation") or ""),
        pacing_hint=str(row.get("pacing_hint") or ""),
        pattern_count=int(row.get("pattern_count") or 0),
        sources=list(row.get("sources") or []),
        signals=dict(row.get("signals") or {}),
    )


def _to_response(report) -> TrendForecastResponse:
    d = report.to_dict()
    return TrendForecastResponse(
        project_id=d["project_id"],
        pipeline_id=d.get("pipeline_id"),
        topic=d["topic"],
        niche=d.get("niche", ""),
        trend_score=float(d["trend_score"]),
        expected_growth=d["expected_growth"],
        production_recommendation=d["production_recommendation"],
        pacing_hint=d.get("pacing_hint", ""),
        pattern_count=int(d.get("pattern_count") or 0),
        sources=list(d.get("sources") or []),
        signals=dict(d.get("signals") or {}),
    )
