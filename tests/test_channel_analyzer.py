"""Channel Analyzer tests — Growth OS Fase 4."""

from __future__ import annotations

import pytest
from contentos_growth.application.channel_analyzer import analyze_channel_snapshot


def _sample_overview() -> dict:
    return {
        "id": "snap-1",
        "fetched_at": "2026-07-09T12:00:00Z",
        "channel_totals": {
            "title": "Canal Teste",
            "description": "Gaming channel #gta #shorts inscreva-se no canal",
            "keywords": "games, reviews",
            "thumbnail_url": "https://img.example/thumb.jpg",
            "custom_url": "@canalteste",
            "subscriber_count": 2500,
            "shorts_count": 2,
            "videos_count": 2,
            "playlists": [{"id": "pl1", "title": "Highlights", "item_count": 5}],
        },
        "media_items": [
            {
                "metrics": {
                    "title": "Short clip #viral",
                    "published_at": "2026-07-08T10:00:00Z",
                    "duration_seconds": 30,
                    "engagement_rate": 0.08,
                    "views": 500,
                }
            },
            {
                "metrics": {
                    "title": "Review completa",
                    "published_at": "2026-07-01T10:00:00Z",
                    "duration_seconds": 420,
                    "engagement_rate": 0.05,
                    "views": 1200,
                }
            },
        ],
    }


def test_analyze_channel_snapshot_scores_and_recommendations():
    result = analyze_channel_snapshot(
        channel_id="ch-1",
        project_id="proj-1",
        platform="youtube",
        channel_name="Canal Teste",
        overview=_sample_overview(),
    )
    assert 0 <= result.score <= 100
    assert result.report["hashtags"]
    assert "inscreva" in result.report["cta_patterns"] or "subscribe" in result.report["cta_patterns"]
    assert result.profile["tone"]
    assert result.recommendations
    assert all(rec.source == "channel_analyzer" for rec in result.recommendations)


def test_analyze_channel_snapshot_requires_overview():
    with pytest.raises(ValueError, match="sincronização"):
        analyze_channel_snapshot(
            channel_id="ch-1",
            project_id="proj-1",
            platform="youtube",
            channel_name="Canal Teste",
            overview=None,
        )


def test_dimensions_present_in_report():
    result = analyze_channel_snapshot(
        channel_id="ch-1",
        project_id="proj-1",
        platform="youtube",
        channel_name="Canal Teste",
        overview=_sample_overview(),
    )
    dims = result.report["dimensions"]
    assert set(dims) == {"branding", "consistency", "format_mix", "engagement", "metadata"}
