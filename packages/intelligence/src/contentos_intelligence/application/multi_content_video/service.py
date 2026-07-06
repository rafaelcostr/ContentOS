"""MultiContentVideoService — platform variants from render (Epic 2b)."""

from __future__ import annotations

import os

from contentos_intelligence.application.multi_content_video.heuristics import GENERATORS
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.video_variants import VIDEO_PLATFORMS, VideoPlatformVariant, VideoVariantsReport


def is_multi_content_video_enabled() -> bool:
    return os.getenv("MULTI_CONTENT_VIDEO_ENABLED", "true").lower() in ("1", "true", "yes")


def _enabled_platforms() -> list[str]:
    raw = os.getenv("MULTI_CONTENT_VIDEO_PLATFORMS", "tiktok,youtube_shorts,instagram_reels")
    platforms = [p.strip() for p in raw.split(",") if p.strip()]
    return [p for p in platforms if p in VIDEO_PLATFORMS]


class MultiContentVideoService:
    def generate(
        self,
        context: IntelligenceContext,
        *,
        platforms: list[str] | None = None,
        llm_variants: dict[str, VideoPlatformVariant] | None = None,
    ) -> VideoVariantsReport:
        payload = dict(context.payload or {})
        target = platforms or _enabled_platforms()
        llm_map = llm_variants or {}
        variants: list[VideoPlatformVariant] = []

        for platform in target:
            generator = GENERATORS.get(platform)
            if not generator:
                continue
            base = generator(payload)
            variants.append(llm_map.get(platform, base))

        return VideoVariantsReport(
            project_id=str(context.project_id),
            pipeline_id=str(context.pipeline_id) if context.pipeline_id else None,
            topic=str(context.topic or ""),
            variants=variants,
        )
