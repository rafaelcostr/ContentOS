"""Platform registry tests — Growth OS Fase 11."""

from __future__ import annotations

from contentos_growth.platform_registry import (
    default_content_type,
    get_platform_profile,
    list_growth_platforms,
    normalize_platform_id,
    to_content_variant_id,
)


def test_normalize_platform_id_aliases():
    assert normalize_platform_id("youtube_shorts") == "youtube"
    assert normalize_platform_id("instagram_reels") == "instagram"
    assert normalize_platform_id("IG") == "instagram"


def test_oauth_platform_profiles():
    oauth = {p.id for p in list_growth_platforms(oauth_only=True)}
    assert oauth == {"youtube", "tiktok", "instagram"}


def test_content_variant_mapping():
    assert to_content_variant_id("youtube") == "youtube_shorts"
    assert to_content_variant_id("instagram") == "instagram_reels"
    assert to_content_variant_id("tiktok") == "tiktok"


def test_default_content_type_per_platform():
    assert default_content_type("tiktok", 0) == "short"
    assert default_content_type("instagram", 0) == "reel"
    assert get_platform_profile("facebook") is not None
    assert get_platform_profile("facebook").analytics_supported is False
