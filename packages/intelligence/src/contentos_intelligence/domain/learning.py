"""Learning Engine domain — Epic 7."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LearningSignal:
    signal_type: str
    value: str
    score: float | None = None
    source: str = "pipeline"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "value": self.value,
            "score": self.score,
            "source": self.source,
            "metadata": dict(self.metadata),
        }


@dataclass
class LearningReport:
    project_id: str
    pipeline_id: str | None
    topic: str
    content_score: float | None = None
    viral_score: float | None = None
    specialist_id: str | None = None
    hook_text: str = ""
    cta_text: str = ""
    signals: list[LearningSignal] = field(default_factory=list)
    memory_applied: bool = False
    memory_updates: list[str] = field(default_factory=list)
    kb_indexed_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "pipeline_id": self.pipeline_id,
            "topic": self.topic,
            "content_score": self.content_score,
            "viral_score": self.viral_score,
            "specialist_id": self.specialist_id,
            "hook_text": self.hook_text,
            "cta_text": self.cta_text,
            "signal_count": len(self.signals),
            "signals": [s.to_dict() for s in self.signals],
            "memory_applied": self.memory_applied,
            "memory_updates": list(self.memory_updates),
            "kb_indexed_count": self.kb_indexed_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LearningReport:
        signals = [
            LearningSignal(
                signal_type=str(s.get("signal_type", "")),
                value=str(s.get("value", "")),
                score=s.get("score"),
                source=str(s.get("source", "pipeline")),
                metadata=dict(s.get("metadata") or {}),
            )
            for s in data.get("signals") or []
        ]
        return cls(
            project_id=str(data.get("project_id", "")),
            pipeline_id=str(data["pipeline_id"]) if data.get("pipeline_id") else None,
            topic=str(data.get("topic", "")),
            content_score=data.get("content_score"),
            viral_score=data.get("viral_score"),
            specialist_id=str(data["specialist_id"]) if data.get("specialist_id") else None,
            hook_text=str(data.get("hook_text") or ""),
            cta_text=str(data.get("cta_text") or ""),
            signals=signals,
            memory_applied=bool(data.get("memory_applied")),
            memory_updates=list(data.get("memory_updates") or []),
            kb_indexed_count=int(data.get("kb_indexed_count") or 0),
        )
