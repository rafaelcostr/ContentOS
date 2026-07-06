"""Viral intelligence report — output of Epic 1 / content_intelligence step."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ViralReport:
    """Aggregated viral analysis delivered to the workflow payload before editor."""

    viral_score: float = 0.0
    retention_prediction: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    hook_score: float | None = None
    rhythm_score: float | None = None
    emotion_score: float | None = None
    scene_score: float | None = None
    cta_score: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "viral_score": round(self.viral_score, 2),
            "retention_prediction": round(self.retention_prediction, 2),
            "recommendations": list(self.recommendations),
            "hook_score": self.hook_score,
            "rhythm_score": self.rhythm_score,
            "emotion_score": self.emotion_score,
            "scene_score": self.scene_score,
            "cta_score": self.cta_score,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ViralReport:
        return cls(
            viral_score=float(data.get("viral_score") or 0),
            retention_prediction=float(data.get("retention_prediction") or 0),
            recommendations=list(data.get("recommendations") or []),
            hook_score=data.get("hook_score"),
            rhythm_score=data.get("rhythm_score"),
            emotion_score=data.get("emotion_score"),
            scene_score=data.get("scene_score"),
            cta_score=data.get("cta_score"),
            details=dict(data.get("details") or {}),
        )
