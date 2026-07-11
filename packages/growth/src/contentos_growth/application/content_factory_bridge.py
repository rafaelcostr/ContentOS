"""Growth → Content Factory bridge (Growth OS Fase 10)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contentos_growth.domain import GrowthStrategy
from contentos_growth.platform_registry import (
    default_content_type,
    get_platform_profile,
    normalize_platform_id,
    to_content_variant_id,
)

_DEFAULT_DURATIONS = {
    "short": 45,
    "reel": 45,
    "video": 60,
    "post": 30,
}


@dataclass(frozen=True)
class GrowthPipelineDispatch:
    project_id: str
    topic: str
    context_json: dict[str, Any]
    calendar_item_id: str | None = None
    workflow_name: str | None = None

    def to_workflow_request(self, *, auto_start: bool = True) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "topic": self.topic,
            "workflow_name": self.workflow_name,
            "context_json": self.context_json,
            "auto_start": auto_start,
        }


def build_growth_context_json(
    *,
    calendar_item: dict[str, Any],
    strategy: GrowthStrategy | None = None,
) -> dict[str, Any]:
    """Contract per docs/GROWTH_OS_RULES.md — Rule 10."""
    metadata = dict(calendar_item.get("metadata") or {})
    topic = str(calendar_item.get("topic") or calendar_item.get("title") or "").strip()
    platform = normalize_platform_id(str(metadata.get("platform") or "youtube"))
    profile = get_platform_profile(platform)
    content_type = str(metadata.get("content_type") or default_content_type(platform)).lower()
    duration = int(
        metadata.get("duration_target_seconds")
        or _DEFAULT_DURATIONS.get(content_type)
        or (profile.max_duration_seconds if profile else None)
        or 60
    )

    objective = ""
    if strategy:
        objective = strategy.positioning or (strategy.goals[0] if strategy.goals else "")
    if not objective:
        objective = topic[:200]

    context: dict[str, Any] = {
        "topic": topic,
        "objective": objective,
        "target_platform": platform,
        "content_variant_id": to_content_variant_id(platform),
        "channel_id": calendar_item.get("channel_id"),
        "brand_context_ref": "project_memory",
        "growth_plan_id": calendar_item.get("id"),
        "growth_strategy_id": strategy.id if strategy else None,
        "growth_source": "growth_calendar",
        "content_type": content_type,
        "campaign": metadata.get("campaign"),
        "duration_target_seconds": duration,
        "planned_for": calendar_item.get("planned_for"),
    }

    if metadata.get("media_strategy"):
        context["media_strategy"] = metadata["media_strategy"]

    if metadata.get("creative_direction"):
        context["creative_direction"] = metadata["creative_direction"]

    if metadata.get("cost_decision"):
        context["cost_decision"] = metadata["cost_decision"]

    if strategy and strategy.cadence.get("posting_hours"):
        context["suggested_posting_hours"] = strategy.cadence["posting_hours"]

    return {key: value for key, value in context.items() if value is not None and value != ""}


def prepare_calendar_dispatch(
    *,
    calendar_item: dict[str, Any],
    strategy: GrowthStrategy | None = None,
    workflow_name: str | None = None,
) -> GrowthPipelineDispatch:
    topic = str(calendar_item.get("topic") or calendar_item.get("title") or "Conteúdo Growth").strip()
    return GrowthPipelineDispatch(
        project_id=str(calendar_item["project_id"]),
        topic=topic[:500],
        context_json=build_growth_context_json(calendar_item=calendar_item, strategy=strategy),
        calendar_item_id=str(calendar_item.get("id")) if calendar_item.get("id") else None,
        workflow_name=workflow_name,
    )
