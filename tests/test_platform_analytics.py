"""V5.4.1 — OAuth Platform Analytics tests."""

from __future__ import annotations

import pytest
from contentos_intelligence.application.platform_analytics.fetchers import _engagement_rate
from contentos_intelligence.application.platform_analytics.service import summarize_snapshots
from contentos_intelligence.domain.platform_metrics import PlatformMediaMetrics
from contentos_shared.oauth_providers import (
    ANALYTICS_OAUTH_SCOPES,
    _merge_scopes,
    get_oauth_config,
    oauth_analytics_enabled,
)


def test_analytics_oauth_scopes_defined():
    assert "youtube" in ANALYTICS_OAUTH_SCOPES
    assert "tiktok" in ANALYTICS_OAUTH_SCOPES
    assert "instagram" in ANALYTICS_OAUTH_SCOPES


def test_merge_scopes_adds_analytics(monkeypatch):
    monkeypatch.setenv("PLATFORM_ANALYTICS_ENABLED", "true")
    merged = _merge_scopes("youtube", ("https://www.googleapis.com/auth/youtube.readonly",))
    assert "https://www.googleapis.com/auth/yt-analytics.readonly" in merged
    assert "https://www.googleapis.com/auth/youtube.readonly" in merged


def test_merge_scopes_disabled_without_flag(monkeypatch):
    monkeypatch.setenv("PLATFORM_ANALYTICS_ENABLED", "false")
    base = ("video.upload",)
    assert _merge_scopes("tiktok", base) == base


def test_engagement_rate():
    assert _engagement_rate(1000, 50, 10, 5) == pytest.approx(0.065)
    assert _engagement_rate(0, 1, 0, 0) is None


def test_summarize_snapshots():
    snapshots = [
        {
            "platform": "youtube",
            "metrics": {"views": 100, "likes": 10, "comments": 2},
        },
        {
            "platform": "youtube",
            "metrics": {"views": 200, "likes": 20, "comments": 4},
        },
        {
            "platform": "tiktok",
            "metrics": {"views": 50, "likes": 5, "comments": 1},
        },
    ]
    summary = summarize_snapshots(snapshots)
    assert summary["snapshot_count"] == 3
    by_name = {p["platform"]: p for p in summary["platforms"]}
    assert by_name["youtube"]["total_views"] == 300
    assert by_name["tiktok"]["media_count"] == 1


def test_platform_media_metrics_roundtrip():
    item = PlatformMediaMetrics(platform="instagram", views=10, likes=2, comments=1, shares=0)
    restored = PlatformMediaMetrics.from_dict(item.to_dict())
    assert restored.views == 10
    assert restored.platform == "instagram"


@pytest.mark.asyncio
async def test_fetch_youtube_missing_token():
    from contentos_intelligence.application.platform_analytics.fetchers import fetch_youtube_analytics

    items, totals = await fetch_youtube_analytics({})
    assert items == []
    assert totals.get("error") == "missing_access_token"


def test_oauth_analytics_enabled_default():
    assert oauth_analytics_enabled() in (True, False)


def test_youtube_config_includes_analytics_scope_when_enabled(monkeypatch):
    monkeypatch.setenv("PLATFORM_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test-id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test-secret")
    cfg = get_oauth_config("youtube")
    assert cfg is not None
    assert any("yt-analytics" in s for s in cfg.scopes)
