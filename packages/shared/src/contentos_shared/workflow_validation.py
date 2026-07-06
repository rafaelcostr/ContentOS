"""Workflow step validation for custom builder (V3 Tier D2)."""

from __future__ import annotations

import re

from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import list_builtin_names

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,48}[a-z0-9]$|^[a-z0-9]$")


def _tier(key: str) -> str:
    if key in (
        "trend_intelligence",
        "hook",
        "script_review",
        "emotion",
        "storyboard",
        "scene_director",
        "video_review",
    ):
        return "v3"
    if key == "content_intelligence":
        return "v4"
    if key == "multi_content":
        return "v4"
    if key == "multi_content_video":
        return "v4"
    if key == "learning":
        return "v4"
    if key == "content_graph":
        return "v4"
    if key in ("clip_research", "asset_collector", "asset_index", "thumbnail", "analytics"):
        return "v2"
    return "core"


STEP_CATALOG: list[dict[str, str]] = [
    {"key": step.value, "label": step.value.replace("_", " ").title(), "tier": _tier(step.value)}
    for step in PipelineStep
]


def all_known_steps() -> set[str]:
    return {step.value for step in PipelineStep}


class WorkflowValidationError(ValueError):
    pass


def validate_slug(slug: str) -> str:
    value = slug.strip().lower()
    if not SLUG_PATTERN.match(value):
        raise WorkflowValidationError(
            "Slug must be lowercase alphanumeric with hyphens (2-50 chars)"
        )
    if value in list_builtin_names():
        raise WorkflowValidationError("Slug conflicts with a built-in workflow name")
    return value


def validate_workflow_steps(steps: list[str]) -> list[str]:
    if not steps:
        raise WorkflowValidationError("At least one step is required")
    known = all_known_steps()
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in steps:
        step = raw.strip()
        if step not in known:
            raise WorkflowValidationError(f"Unknown step: {step}")
        if step in seen:
            raise WorkflowValidationError(f"Duplicate step: {step}")
        seen.add(step)
        normalized.append(step)
    return normalized


def custom_workflow_name(org_id: str, slug: str) -> str:
    return f"org-{org_id}-{slug}"
