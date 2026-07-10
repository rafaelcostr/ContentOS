"""Per-platform channel analyzer tests — Growth OS Fase 11."""

from __future__ import annotations

from contentos_growth.application.channel_analyzer import analyze_channel_snapshot


def _instagram_overview() -> dict:
    return {
        "id": "ig-1",
        "fetched_at": "2026-07-09T12:00:00Z",
        "channel_totals": {"username": "brandco", "followers_count": 1200, "media_count": 8},
        "media_items": [
            {
                "metrics": {
                    "title": "Novo reel #marketing #growth",
                    "published_at": "2026-07-08T10:00:00Z",
                    "views": 800,
                    "engagement_rate": 0.06,
                }
            },
            {
                "metrics": {
                    "title": "Bastidores do time",
                    "published_at": "2026-07-05T10:00:00Z",
                    "views": 500,
                    "engagement_rate": 0.04,
                }
            },
        ],
    }


def _tiktok_overview() -> dict:
    return {
        "id": "tt-1",
        "fetched_at": "2026-07-09T12:00:00Z",
        "channel_totals": {"display_name": "BrandCo", "follower_count": 5000, "video_count": 12, "likes_count": 20000},
        "media_items": [
            {
                "metrics": {
                    "title": "Hook viral #fyp",
                    "published_at": "2026-07-08T10:00:00Z",
                    "views": 12000,
                    "shares": 80,
                    "engagement_rate": 0.09,
                }
            }
        ],
    }


def test_analyze_instagram_channel():
    result = analyze_channel_snapshot(
        channel_id="ch-ig",
        project_id="proj-1",
        platform="instagram",
        channel_name="BrandCo",
        overview=_instagram_overview(),
    )
    assert result.platform == "instagram"
    assert 0 <= result.score <= 100
    assert result.report["hashtags"]
    assert result.report["data_source"]["platform"] == "instagram"


def test_analyze_tiktok_channel():
    result = analyze_channel_snapshot(
        channel_id="ch-tt",
        project_id="proj-1",
        platform="tiktok",
        channel_name="BrandCo",
        overview=_tiktok_overview(),
    )
    assert result.platform == "tiktok"
    assert result.profile["follower_count"] == 5000
    assert result.recommendations


def test_analyze_requires_sync_data_with_platform_label():
    try:
        analyze_channel_snapshot(
            channel_id="ch-tt",
            project_id="proj-1",
            platform="tiktok",
            channel_name="BrandCo",
            overview=None,
        )
    except ValueError as exc:
        assert "TikTok" in str(exc)
    else:
        raise AssertionError("expected ValueError")
