"""Heuristic video platform metadata from render + publication — Epic 2b."""

from __future__ import annotations

from typing import Any

from contentos_intelligence.application.multi_content_video.specs import (
    PLATFORM_DESC_LIMITS,
    PLATFORM_SPECS,
    PLATFORM_TITLE_LIMITS,
)
from contentos_intelligence.domain.video_variants import VideoPlatformVariant


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _publication(payload: dict) -> dict:
    pub = payload.get("publication") or {}
    return pub if isinstance(pub, dict) else {}


def _base_title_description(payload: dict) -> tuple[str, str, list[str]]:
    pub = _publication(payload)
    script = payload.get("script") or {}
    title = str(pub.get("title") or (script.get("title") if isinstance(script, dict) else "") or payload.get("topic") or "")
    description = str(pub.get("description") or "")
    if not description and isinstance(script, dict):
        description = str(script.get("full_text") or script.get("hook") or "")[:500]
    hashtags = list(pub.get("hashtags") or [])
    if not hashtags:
        hashtags = ["viral", "shorts", "conteudo"]
    return title, description, hashtags


def _render_ref(payload: dict) -> dict[str, Any] | None:
    ref = payload.get("render_ref")
    if isinstance(ref, dict) and ref.get("id"):
        return dict(ref)
    return None


def _platform_metadata(platform: str, payload: dict) -> dict[str, Any]:
    duration = payload.get("duration_seconds")
    if duration is None:
        script = payload.get("script") or {}
        if isinstance(script, dict):
            duration = script.get("duration_seconds")
    meta: dict[str, Any] = {"ready_to_publish": bool(_render_ref(payload))}
    if duration is not None:
        try:
            meta["duration_seconds"] = float(duration)
        except (TypeError, ValueError):
            pass
    if platform == "youtube_shorts":
        meta["is_short"] = True
        meta["category"] = "shorts"
    if platform == "instagram_reels":
        meta["share_to_feed"] = True
    if platform == "tiktok":
        meta["allow_duet"] = True
        meta["allow_stitch"] = True
    return meta


def generate_variant(platform: str, payload: dict) -> VideoPlatformVariant:
    title, description, hashtags = _base_title_description(payload)
    spec = PLATFORM_SPECS[platform]
    title_limit = PLATFORM_TITLE_LIMITS.get(platform, 100)
    desc_limit = PLATFORM_DESC_LIMITS.get(platform, 2000)

    platform_title = title
    platform_desc = description
    platform_tags = list(hashtags)

    if platform == "youtube_shorts":
        platform_title = _truncate(title, title_limit)
        if "#shorts" not in " ".join(platform_tags).lower():
            platform_tags = ["shorts", *platform_tags[:8]]
        platform_desc = _truncate(f"{description}\n\n#Shorts", desc_limit)
    elif platform == "instagram_reels":
        platform_title = _truncate(title, title_limit)
        platform_desc = _truncate(description, desc_limit)
        platform_tags = platform_tags[:30]
    else:
        platform_title = _truncate(title, title_limit)
        platform_desc = _truncate(description, desc_limit)
        platform_tags = platform_tags[:10]

    return VideoPlatformVariant(
        platform=platform,
        title=platform_title,
        description=platform_desc,
        hashtags=platform_tags,
        crop_spec=spec,
        render_ref=_render_ref(payload),
        metadata=_platform_metadata(platform, payload),
        source="heuristic",
    )


GENERATORS = {
    "tiktok": lambda p: generate_variant("tiktok", p),
    "youtube_shorts": lambda p: generate_variant("youtube_shorts", p),
    "instagram_reels": lambda p: generate_variant("instagram_reels", p),
}


def merge_llm_variant(platform: str, llm_data: dict[str, Any], fallback: VideoPlatformVariant) -> VideoPlatformVariant:
    title = _truncate(str(llm_data.get("title") or fallback.title), PLATFORM_TITLE_LIMITS.get(platform, 100))
    description = _truncate(
        str(llm_data.get("description") or fallback.description),
        PLATFORM_DESC_LIMITS.get(platform, 2000),
    )
    hashtags = llm_data.get("hashtags")
    if not isinstance(hashtags, list):
        hashtags = fallback.hashtags
    extra = {k: v for k, v in llm_data.items() if k not in ("title", "description", "hashtags")}
    return VideoPlatformVariant(
        platform=platform,
        title=title,
        description=description,
        hashtags=[str(h).lstrip("#") for h in hashtags][:15],
        crop_spec=fallback.crop_spec,
        render_ref=fallback.render_ref,
        metadata={**fallback.metadata, **extra},
        source="llm",
    )
