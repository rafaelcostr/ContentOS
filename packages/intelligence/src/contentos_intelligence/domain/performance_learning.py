"""Performance Learning domain — V5.4.2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerformanceMediaInsight:
    platform: str
    external_media_id: str | None
    title: str | None
    topic: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    ctr: float | None = None
    engagement_rate: float | None = None
    retention_pct: float | None = None
    predicted_retention_pct: float | None = None
    retention_delta: float | None = None
    performance_tier: str = "medium"
    pipeline_id: str | None = None
    hook_text: str | None = None
    learnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "external_media_id": self.external_media_id,
            "title": self.title,
            "topic": self.topic,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "ctr": self.ctr,
            "engagement_rate": self.engagement_rate,
            "retention_pct": self.retention_pct,
            "predicted_retention_pct": self.predicted_retention_pct,
            "retention_delta": self.retention_delta,
            "performance_tier": self.performance_tier,
            "pipeline_id": self.pipeline_id,
            "hook_text": self.hook_text,
            "learnings": list(self.learnings),
        }


@dataclass
class PerformanceLearningReport:
    project_id: str
    media_insights: list[PerformanceMediaInsight] = field(default_factory=list)
    top_performers: list[PerformanceMediaInsight] = field(default_factory=list)
    kb_indexed_count: int = 0
    memory_applied: bool = False
    memory_updates: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "media_insights": [m.to_dict() for m in self.media_insights],
            "top_performers": [m.to_dict() for m in self.top_performers],
            "kb_indexed_count": self.kb_indexed_count,
            "memory_applied": self.memory_applied,
            "memory_updates": list(self.memory_updates),
            "summary": self.summary,
        }
