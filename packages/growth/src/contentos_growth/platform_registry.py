"""Canonical platform profiles for Growth OS (Fase 11)."""

from __future__ import annotations

from dataclasses import dataclass

_PLATFORM_ALIASES = {
    "youtube_shorts": "youtube",
    "instagram_reels": "instagram",
    "ig": "instagram",
    "yt": "youtube",
}


@dataclass(frozen=True)
class PlatformProfile:
    id: str
    label: str
    oauth_supported: bool
    analytics_supported: bool
    publish_supported: bool
    content_variant_id: str | None
    content_types: tuple[str, ...]
    follower_field: str
    primary_metric: str
    max_duration_seconds: int | None
    weekly_posts_default: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "oauth_supported": self.oauth_supported,
            "analytics_supported": self.analytics_supported,
            "publish_supported": self.publish_supported,
            "content_variant_id": self.content_variant_id,
            "content_types": list(self.content_types),
            "follower_field": self.follower_field,
            "primary_metric": self.primary_metric,
            "max_duration_seconds": self.max_duration_seconds,
            "weekly_posts_default": self.weekly_posts_default,
        }


_PROFILES: dict[str, PlatformProfile] = {
    "youtube": PlatformProfile(
        id="youtube",
        label="YouTube",
        oauth_supported=True,
        analytics_supported=True,
        publish_supported=True,
        content_variant_id="youtube_shorts",
        content_types=("short", "video"),
        follower_field="subscriber_count",
        primary_metric="views",
        max_duration_seconds=60,
        weekly_posts_default=3,
    ),
    "instagram": PlatformProfile(
        id="instagram",
        label="Instagram",
        oauth_supported=True,
        analytics_supported=True,
        publish_supported=True,
        content_variant_id="instagram_reels",
        content_types=("reel", "post"),
        follower_field="followers_count",
        primary_metric="impressions",
        max_duration_seconds=90,
        weekly_posts_default=4,
    ),
    "tiktok": PlatformProfile(
        id="tiktok",
        label="TikTok",
        oauth_supported=True,
        analytics_supported=True,
        publish_supported=True,
        content_variant_id="tiktok",
        content_types=("short",),
        follower_field="follower_count",
        primary_metric="views",
        max_duration_seconds=60,
        weekly_posts_default=5,
    ),
    "facebook": PlatformProfile(
        id="facebook",
        label="Facebook",
        oauth_supported=False,
        analytics_supported=False,
        publish_supported=False,
        content_variant_id=None,
        content_types=("post", "video"),
        follower_field="followers_count",
        primary_metric="reach",
        max_duration_seconds=None,
        weekly_posts_default=3,
    ),
    "threads": PlatformProfile(
        id="threads",
        label="Threads",
        oauth_supported=False,
        analytics_supported=False,
        publish_supported=False,
        content_variant_id=None,
        content_types=("post",),
        follower_field="followers_count",
        primary_metric="views",
        max_duration_seconds=None,
        weekly_posts_default=4,
    ),
    "pinterest": PlatformProfile(
        id="pinterest",
        label="Pinterest",
        oauth_supported=False,
        analytics_supported=False,
        publish_supported=False,
        content_variant_id=None,
        content_types=("pin",),
        follower_field="followers_count",
        primary_metric="impressions",
        max_duration_seconds=None,
        weekly_posts_default=3,
    ),
    "linkedin": PlatformProfile(
        id="linkedin",
        label="LinkedIn",
        oauth_supported=False,
        analytics_supported=False,
        publish_supported=False,
        content_variant_id=None,
        content_types=("post",),
        follower_field="followers_count",
        primary_metric="impressions",
        max_duration_seconds=None,
        weekly_posts_default=2,
    ),
    "x": PlatformProfile(
        id="x",
        label="X",
        oauth_supported=False,
        analytics_supported=False,
        publish_supported=False,
        content_variant_id=None,
        content_types=("post",),
        follower_field="followers_count",
        primary_metric="impressions",
        max_duration_seconds=None,
        weekly_posts_default=5,
    ),
}


def normalize_platform_id(platform: str | None) -> str:
    raw = (platform or "").strip().lower()
    return _PLATFORM_ALIASES.get(raw, raw)


def get_platform_profile(platform: str | None) -> PlatformProfile | None:
    return _PROFILES.get(normalize_platform_id(platform))


def list_growth_platforms(*, oauth_only: bool = False) -> list[PlatformProfile]:
    profiles = list(_PROFILES.values())
    if oauth_only:
        profiles = [p for p in profiles if p.oauth_supported]
    return profiles


def to_content_variant_id(platform: str | None) -> str | None:
    profile = get_platform_profile(platform)
    return profile.content_variant_id if profile else None


def default_content_type(platform: str | None, index: int = 0) -> str:
    profile = get_platform_profile(platform)
    if not profile or not profile.content_types:
        return "video"
    types = profile.content_types
    return types[index % len(types)]
