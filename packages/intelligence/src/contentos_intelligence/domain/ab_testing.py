"""A/B testing domain models — Epic 6."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

AB_DIMENSIONS = frozenset({"hook", "title", "cta", "thumbnail", "opener"})


@dataclass
class AbVariant:
    variant_id: str
    value: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "value": self.value,
            "score": round(self.score, 2),
            "metadata": dict(self.metadata),
        }


@dataclass
class AbDimensionResult:
    dimension: str
    variants: list[AbVariant] = field(default_factory=list)
    winner_index: int = 0
    winner: AbVariant | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "variants": [v.to_dict() for v in self.variants],
            "winner_index": self.winner_index,
            "winner": self.winner.to_dict() if self.winner else None,
        }


@dataclass
class AbTestReport:
    project_id: UUID
    pipeline_id: UUID | None
    dimensions: list[AbDimensionResult] = field(default_factory=list)
    winners: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "pipeline_id": str(self.pipeline_id) if self.pipeline_id else None,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "winners": dict(self.winners),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AbTestReport:
        dims: list[AbDimensionResult] = []
        for dim_data in data.get("dimensions") or []:
            variants = [
                AbVariant(
                    variant_id=v.get("variant_id", ""),
                    value=v.get("value", ""),
                    score=float(v.get("score", 0)),
                    metadata=v.get("metadata") or {},
                )
                for v in dim_data.get("variants") or []
            ]
            winner_data = dim_data.get("winner")
            winner = None
            if winner_data:
                winner = AbVariant(
                    variant_id=winner_data.get("variant_id", ""),
                    value=winner_data.get("value", ""),
                    score=float(winner_data.get("score", 0)),
                    metadata=winner_data.get("metadata") or {},
                )
            dims.append(
                AbDimensionResult(
                    dimension=str(dim_data.get("dimension", "")),
                    variants=variants,
                    winner_index=int(dim_data.get("winner_index", 0)),
                    winner=winner,
                )
            )
        project_id = data.get("project_id")
        pipeline_id = data.get("pipeline_id")
        return cls(
            project_id=UUID(str(project_id)) if project_id else uuid4(),
            pipeline_id=UUID(str(pipeline_id)) if pipeline_id else None,
            dimensions=dims,
            winners=dict(data.get("winners") or {}),
        )


def new_variant_id() -> str:
    return str(uuid4())
