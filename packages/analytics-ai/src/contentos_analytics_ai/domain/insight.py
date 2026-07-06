"""Analytics insight domain model."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class AnalyticsInsightData:
    project_id: UUID
    pipeline_id: UUID
    metrics: dict[str, Any] = field(default_factory=dict)
    analysis: dict[str, Any] = field(default_factory=dict)
    models_used: dict[str, Any] = field(default_factory=dict)
    prompts_used: dict[str, Any] = field(default_factory=dict)
    applied_to_memory: bool = False
    video_id: UUID | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "pipeline_id": str(self.pipeline_id),
            "video_id": str(self.video_id) if self.video_id else None,
            "metrics": self.metrics,
            "analysis": self.analysis,
            "models_used": self.models_used,
            "prompts_used": self.prompts_used,
            "applied_to_memory": self.applied_to_memory,
            "score": self.analysis.get("score"),
            "summary": self.analysis.get("summary"),
        }
