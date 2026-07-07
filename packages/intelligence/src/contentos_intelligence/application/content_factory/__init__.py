"""Content Factory — batch production (V5.3)."""

from contentos_intelligence.application.content_factory.service import (
    assert_batch_can_start,
    build_batch_plan,
    create_content_batch,
    estimate_batch_cost,
    factory_default_require_approval,
    factory_enabled,
    factory_max_batch_size,
    mark_batch_publish_approved,
    pipeline_context_for_variant,
    refresh_batch_variant_statuses,
)
from contentos_intelligence.application.content_factory.variation import hook_hint_for_angle, plan_variations

__all__ = [
    "assert_batch_can_start",
    "build_batch_plan",
    "create_content_batch",
    "estimate_batch_cost",
    "factory_default_require_approval",
    "factory_enabled",
    "factory_max_batch_size",
    "hook_hint_for_angle",
    "mark_batch_publish_approved",
    "pipeline_context_for_variant",
    "plan_variations",
    "refresh_batch_variant_statuses",
]
