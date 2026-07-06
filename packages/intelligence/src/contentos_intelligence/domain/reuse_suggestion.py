"""Smart reuse suggestions — Epic 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class ReuseSuggestion:
    """A single reusable asset from the knowledge base."""

    resource_type: str
    resource_id: UUID | None
    title: str
    similarity: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "title": self.title,
            "similarity": round(self.similarity, 4),
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }
