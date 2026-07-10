"""Post Manager — Growth orchestration for text posts (Growth OS Fase 12)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contentos_growth.domain import GrowthStrategy
from contentos_growth.platform_registry import default_content_type, get_platform_profile, normalize_platform_id

TEXT_CONTENT_TYPES = frozenset({"post", "pin", "thread"})
VIDEO_CONTENT_TYPES = frozenset({"short", "video", "reel", "content"})

_PLATFORM_TEXT_FORMATS: dict[str, tuple[str, ...]] = {
    "x": ("thread_x",),
    "threads": ("thread_x",),
    "linkedin": ("linkedin_post",),
    "instagram": ("linkedin_post",),
    "facebook": ("linkedin_post",),
    "pinterest": ("seo_article",),
    "youtube": ("seo_article", "newsletter"),
    "tiktok": (),
}

_VIDEO_COMPANION_FORMATS: dict[str, tuple[str, ...]] = {
    "linkedin": ("linkedin_post",),
    "x": ("thread_x",),
    "threads": ("thread_x",),
    "youtube": ("seo_article",),
}


@dataclass(frozen=True)
class PostGenerationPlan:
    calendar_item_id: str
    project_id: str
    topic: str
    platform: str
    content_type: str
    mode: str
    text_formats: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PostGenerationResult:
    calendar_item_id: str
    project_id: str
    topic: str
    platform: str
    content_type: str
    formats: list[str]
    artifacts: list[dict[str, Any]]
    report: dict[str, Any]


def is_text_content_type(content_type: str | None) -> bool:
    return (content_type or "").lower() in TEXT_CONTENT_TYPES


def is_video_content_type(content_type: str | None) -> bool:
    normalized = (content_type or "").lower()
    return normalized in VIDEO_CONTENT_TYPES or normalized not in TEXT_CONTENT_TYPES


def resolve_text_formats(
    platform: str,
    content_type: str,
    *,
    include_companion: bool = False,
) -> list[str]:
    normalized_platform = normalize_platform_id(platform)
    normalized_type = (content_type or "").lower()

    if is_text_content_type(normalized_type):
        formats = list(_PLATFORM_TEXT_FORMATS.get(normalized_platform, ("linkedin_post",)))
        return [fmt for fmt in formats if fmt]

    if include_companion:
        companion = _VIDEO_COMPANION_FORMATS.get(normalized_platform, ())
        return list(companion)

    profile = get_platform_profile(normalized_platform)
    if profile and "post" in profile.content_types and normalized_platform in _PLATFORM_TEXT_FORMATS:
        return list(_PLATFORM_TEXT_FORMATS[normalized_platform][:1])
    return []


def build_post_payload(
    *,
    calendar_item: dict[str, Any],
    strategy: GrowthStrategy | None = None,
) -> dict[str, Any]:
    metadata = dict(calendar_item.get("metadata") or {})
    platform = normalize_platform_id(str(metadata.get("platform") or "youtube"))
    content_type = str(metadata.get("content_type") or default_content_type(platform)).lower()
    topic = str(calendar_item.get("topic") or calendar_item.get("title") or "").strip()
    title = str(calendar_item.get("title") or topic or "Conteúdo Growth").strip()
    objective = ""
    if strategy:
        objective = strategy.positioning or (strategy.goals[0] if strategy.goals else "")

    return {
        "topic": topic or title,
        "script": {
            "title": title,
            "full_text": topic or title,
            "hook": (topic or title)[:160],
            "call_to_action": objective[:200] if objective else "Comente o que achou!",
        },
        "target_platform": platform,
        "content_type": content_type,
        "channel_id": calendar_item.get("channel_id"),
        "growth_plan_id": calendar_item.get("id"),
        "growth_strategy_id": strategy.id if strategy else None,
        "growth_source": "growth_post_manager",
        "campaign": metadata.get("campaign"),
        "planned_for": calendar_item.get("planned_for"),
        "objective": objective,
    }


def plan_calendar_post(
    *,
    calendar_item: dict[str, Any],
    strategy: GrowthStrategy | None = None,
    include_companion: bool = False,
) -> PostGenerationPlan:
    metadata = dict(calendar_item.get("metadata") or {})
    platform = normalize_platform_id(str(metadata.get("platform") or "youtube"))
    content_type = str(metadata.get("content_type") or default_content_type(platform)).lower()
    topic = str(calendar_item.get("topic") or calendar_item.get("title") or "Conteúdo Growth").strip()
    mode = "text" if is_text_content_type(content_type) else "video"
    formats = resolve_text_formats(platform, content_type, include_companion=include_companion)

    return PostGenerationPlan(
        calendar_item_id=str(calendar_item.get("id") or ""),
        project_id=str(calendar_item["project_id"]),
        topic=topic[:500],
        platform=platform,
        content_type=content_type,
        mode=mode,
        text_formats=tuple(formats),
        payload=build_post_payload(calendar_item=calendar_item, strategy=strategy),
    )


def generate_post_report(
    *,
    plan: PostGenerationPlan,
    formats: list[str] | None = None,
) -> PostGenerationResult:
    from contentos_intelligence.application.multi_content.service import MultiContentService, is_multi_content_enabled
    from contentos_intelligence.domain.context import IntelligenceContext

    if not is_multi_content_enabled():
        raise ValueError("Multi Content disabled (MULTI_CONTENT_ENABLED=false)")

    target_formats = formats or list(plan.text_formats)
    if not target_formats:
        raise ValueError(f"No text formats configured for platform {plan.platform} / type {plan.content_type}")

    context = IntelligenceContext(
        project_id=plan.project_id,
        pipeline_id=None,
        topic=plan.topic,
        payload=dict(plan.payload),
    )
    report = MultiContentService().generate(context, formats=target_formats)
    report_dict = report.to_dict()
    artifacts = [dict(a) for a in report_dict.get("artifacts") or []]

    return PostGenerationResult(
        calendar_item_id=plan.calendar_item_id,
        project_id=plan.project_id,
        topic=plan.topic,
        platform=plan.platform,
        content_type=plan.content_type,
        formats=target_formats,
        artifacts=artifacts,
        report=report_dict,
    )
