"""Channel analysis result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contentos_growth.domain import GrowthRecommendation


@dataclass(frozen=True)
class ChannelAnalysisResult:
    channel_id: str
    project_id: str
    platform: str
    channel_name: str
    score: float
    summary: str
    report: dict[str, Any]
    profile: dict[str, Any]
    recommendations: list[GrowthRecommendation] = field(default_factory=list)
    analyzed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "platform": self.platform,
            "channel_name": self.channel_name,
            "score": self.score,
            "summary": self.summary,
            "report": dict(self.report),
            "profile": dict(self.profile),
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "analyzed_at": self.analyzed_at,
        }
