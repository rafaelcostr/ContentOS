"""Content Factory batch domain — V5.3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BatchVariant:
    index: int
    topic: str
    content_angle: str
    hook_hint: str
    pipeline_id: str | None = None
    pipeline_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "topic": self.topic,
            "content_angle": self.content_angle,
            "hook_hint": self.hook_hint,
            "pipeline_id": self.pipeline_id,
            "pipeline_status": self.pipeline_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BatchVariant:
        return cls(
            index=int(data.get("index", 0)),
            topic=str(data.get("topic", "")),
            content_angle=str(data.get("content_angle", "")),
            hook_hint=str(data.get("hook_hint", "")),
            pipeline_id=data.get("pipeline_id"),
            pipeline_status=data.get("pipeline_status"),
        )


@dataclass
class BatchCostEstimate:
    quantity: int
    credit_cost_per_pipeline: int
    total_credit_cost: int
    monthly_quota: int
    monthly_used: int
    monthly_remaining: int | None
    concurrent_limit: int
    concurrent_active: int
    quota_ok: bool
    credits_ok: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "quantity": self.quantity,
            "credit_cost_per_pipeline": self.credit_cost_per_pipeline,
            "total_credit_cost": self.total_credit_cost,
            "monthly_quota": self.monthly_quota,
            "monthly_used": self.monthly_used,
            "monthly_remaining": self.monthly_remaining,
            "concurrent_limit": self.concurrent_limit,
            "concurrent_active": self.concurrent_active,
            "quota_ok": self.quota_ok,
            "credits_ok": self.credits_ok,
        }


@dataclass
class BatchPlan:
    topic: str
    workflow_name: str | None
    quantity: int
    require_approval: bool
    variants: list[BatchVariant] = field(default_factory=list)
    cost_estimate: BatchCostEstimate | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "workflow_name": self.workflow_name,
            "quantity": self.quantity,
            "require_approval": self.require_approval,
            "variants": [v.to_dict() for v in self.variants],
            "cost_estimate": self.cost_estimate.to_dict() if self.cost_estimate else None,
        }
