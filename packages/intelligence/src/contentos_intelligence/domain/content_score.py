"""Unified content score 0–100 — Epic 9 facade."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContentScoreDimension:
    name: str
    score: float
    weight: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 2),
            "weight": self.weight,
            "source": self.source,
        }


@dataclass
class ContentScoreReport:
    """Aggregated 0–100 score across hook, retention, emotion, CTA, etc."""

    total_score: float = 0.0
    dimensions: list[ContentScoreDimension] = field(default_factory=list)
    summary: str = ""
    grade: str = ""
    mode: str = "preview"

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_score": round(self.total_score, 2),
            "dimensions": [d.to_dict() for d in self.dimensions],
            "summary": self.summary,
            "grade": self.grade,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContentScoreReport:
        dims = [
            ContentScoreDimension(
                name=str(d.get("name", "")),
                score=float(d.get("score", 0)),
                weight=float(d.get("weight", 0)),
                source=str(d.get("source", "")),
            )
            for d in data.get("dimensions") or []
        ]
        return cls(
            total_score=float(data.get("total_score", 0)),
            dimensions=dims,
            summary=str(data.get("summary", "")),
            grade=str(data.get("grade", "")),
            mode=str(data.get("mode", "preview")),
        )
