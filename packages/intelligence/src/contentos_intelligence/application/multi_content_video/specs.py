"""Platform crop and metadata limits — Epic 2b."""

from __future__ import annotations

from contentos_intelligence.domain.video_variants import CropSpec

PLATFORM_SPECS: dict[str, CropSpec] = {
    "tiktok": CropSpec(
        width=1080,
        height=1920,
        crop_bias="center",
        max_duration_seconds=180,
        safe_zone="tiktok_ui_bottom",
    ),
    "youtube_shorts": CropSpec(
        width=1080,
        height=1920,
        crop_bias="center",
        max_duration_seconds=60,
        safe_zone="shorts_subscribe_overlay",
    ),
    "instagram_reels": CropSpec(
        width=1080,
        height=1920,
        crop_bias="top",
        max_duration_seconds=90,
        safe_zone="reels_caption_top",
    ),
}

PLATFORM_TITLE_LIMITS: dict[str, int] = {
    "tiktok": 150,
    "youtube_shorts": 100,
    "instagram_reels": 100,
}

PLATFORM_DESC_LIMITS: dict[str, int] = {
    "tiktok": 2200,
    "youtube_shorts": 5000,
    "instagram_reels": 2200,
}
