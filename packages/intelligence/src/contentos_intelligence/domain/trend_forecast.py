"""Trend Forecast domain — Epic 10."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

GROWTH_LEVELS = frozenset({"low", "moderate", "high", "very_high"})


@dataclass
class TrendForecastReport:
    project_id: str
    pipeline_id: str | None
    topic: str
    niche: str = ""
    trend_score: float = 50.0
    expected_growth: str = "moderate"
    production_recommendation: str = ""
    pacing_hint: str = ""
    pattern_count: int = 0
    sources: list[str] = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "pipeline_id": self.pipeline_id,
            "topic": self.topic,
            "niche": self.niche,
            "trend_score": round(self.trend_score, 1),
            "expected_growth": self.expected_growth,
            "production_recommendation": self.production_recommendation,
            "pacing_hint": self.pacing_hint,
            "pattern_count": self.pattern_count,
            "sources": list(self.sources),
            "signals": dict(self.signals),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrendForecastReport:
        return cls(
            project_id=str(data.get("project_id", "")),
            pipeline_id=str(data["pipeline_id"]) if data.get("pipeline_id") else None,
            topic=str(data.get("topic", "")),
            niche=str(data.get("niche", "")),
            trend_score=float(data.get("trend_score", 50)),
            expected_growth=str(data.get("expected_growth", "moderate")),
            production_recommendation=str(data.get("production_recommendation", "")),
            pacing_hint=str(data.get("pacing_hint", "")),
            pattern_count=int(data.get("pattern_count") or 0),
            sources=list(data.get("sources") or []),
            signals=dict(data.get("signals") or {}),
        )
