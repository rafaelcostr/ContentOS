"""TrendForecastService — Epic 10."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from contentos_shared.payload_utils import coerce_dict
from contentos_shared.trend_intelligence import build_trend_brief

from contentos_intelligence.application.trend_forecast.heuristics import (
    build_production_recommendation,
    compute_expected_growth,
    compute_trend_score,
)
from contentos_intelligence.domain.trend_forecast import TrendForecastReport


def is_trend_forecast_enabled() -> bool:
    return os.getenv("TREND_FORECAST_ENABLED", "true").lower() in ("1", "true", "yes")


class TrendForecastService:
    def forecast(
        self,
        *,
        project_id: UUID,
        pipeline_id: UUID | None,
        topic: str,
        niche: str = "",
        memory: Any = None,
        insights: list[dict] | None = None,
        learning_rows: list[dict] | None = None,
        kb_entry_count: int = 0,
        trend_brief: dict[str, Any] | None = None,
    ) -> TrendForecastReport:
        mem = coerce_dict(memory.to_dict() if hasattr(memory, "to_dict") else memory)
        insight_rows = insights or []
        learning = learning_rows or []
        brief = trend_brief or build_trend_brief(
            topic=topic,
            niche=niche or str(mem.get("niche") or ""),
            memory=mem,
            insights=insight_rows,
        )
        niche_resolved = str(brief.get("niche") or niche or mem.get("niche") or "")

        trend_score, signals = compute_trend_score(
            brief=brief,
            memory=mem,
            insights=insight_rows,
            learning_rows=learning,
            kb_entry_count=kb_entry_count,
        )
        expected_growth = compute_expected_growth(trend_score, insight_rows, learning)
        recommendation = build_production_recommendation(
            trend_score=trend_score,
            expected_growth=expected_growth,
            brief=brief,
            topic=topic,
        )

        return TrendForecastReport(
            project_id=str(project_id),
            pipeline_id=str(pipeline_id) if pipeline_id else None,
            topic=topic,
            niche=niche_resolved,
            trend_score=trend_score,
            expected_growth=expected_growth,
            production_recommendation=recommendation,
            pacing_hint=str(brief.get("pacing_hint") or ""),
            pattern_count=len(brief.get("patterns") or []),
            sources=list(brief.get("sources") or []),
            signals=signals,
        )
