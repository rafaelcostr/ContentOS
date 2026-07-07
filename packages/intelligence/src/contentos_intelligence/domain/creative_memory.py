"""Creative Memory — merged KB + Learning (V5.2.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CreativeMemoryHit:
    resource_type: str
    title: str
    snippet: str
    similarity: float
    source: str = "knowledge_base"

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "title": self.title,
            "snippet": self.snippet,
            "similarity": round(self.similarity, 4),
            "source": self.source,
        }


@dataclass
class CreativeMemoryReport:
    project_id: str
    pipeline_id: str | None
    topic: str
    learning_report: dict[str, Any]
    knowledge_hits: list[CreativeMemoryHit]
    memory_applied: bool
    memory_updates: list[str]
    kb_indexed_count: int
    knowledge_indexed_count: int
    creative_memory_context: str
    hints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "pipeline_id": self.pipeline_id,
            "topic": self.topic,
            "learning_report": dict(self.learning_report),
            "knowledge_hits": [h.to_dict() for h in self.knowledge_hits],
            "memory_applied": self.memory_applied,
            "memory_updates": list(self.memory_updates),
            "kb_indexed_count": self.kb_indexed_count,
            "knowledge_indexed_count": self.knowledge_indexed_count,
            "creative_memory_context": self.creative_memory_context,
            "hints": dict(self.hints),
        }
