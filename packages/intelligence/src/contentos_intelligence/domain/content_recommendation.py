"""Content recommendations for next videos — phase 7.5."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContentRecommendation:
    kind: str
    title: str
    detail: str
    confidence: str = "medium"
    source: str = "performance_learning"
    action_href: str = "/factory"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "detail": self.detail,
            "confidence": self.confidence,
            "source": self.source,
            "action_href": self.action_href,
        }


@dataclass
class ContentRecommendationReport:
    project_id: str
    recommendations: list[ContentRecommendation] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "summary": self.summary,
            "recommendations": [r.to_dict() for r in self.recommendations],
        }
