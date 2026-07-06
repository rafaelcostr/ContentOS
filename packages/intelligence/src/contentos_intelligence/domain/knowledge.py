"""Knowledge base query types — Epic 3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class KnowledgeQueryRequest:
    project_id: UUID
    query: str
    resource_types: list[str] = field(default_factory=list)
    limit: int = 10
    min_similarity: float = 0.0
    org_id: UUID | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "query": self.query,
            "resource_types": list(self.resource_types),
            "limit": self.limit,
            "min_similarity": self.min_similarity,
            "org_id": str(self.org_id) if self.org_id else None,
        }


@dataclass
class KnowledgeHit:
    resource_type: str
    resource_id: UUID | None
    title: str
    snippet: str
    similarity: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "title": self.title,
            "snippet": self.snippet,
            "similarity": round(self.similarity, 4),
            "metadata": dict(self.metadata),
        }
