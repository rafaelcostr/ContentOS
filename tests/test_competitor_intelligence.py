"""Tests for Competitor Intelligence — Growth OS Fase 7."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_growth.application.competitor_analyzer import analyze_competitor_snapshot
from contentos_intelligence.application.platform_analytics.youtube_public import (
    normalize_youtube_ref,
    resolve_youtube_api_key,
)


def test_normalize_youtube_ref_handle():
    assert normalize_youtube_ref("@creator") == ("handle", "creator")
    assert normalize_youtube_ref("creator") == ("handle", "creator")


def test_normalize_youtube_ref_channel_url():
    kind, value = normalize_youtube_ref("https://www.youtube.com/@MyChannel")
    assert kind == "handle"
    assert value == "MyChannel"


def test_analyze_competitor_snapshot_patterns():
    competitor_id = str(uuid4())
    project_id = str(uuid4())
    metrics = {
        "channel_totals": {
            "title": "Rival Channel",
            "description": "Gaming content #fps #competitive",
            "subscriber_count": 50000,
            "shorts_count": 2,
            "videos_count": 1,
        },
        "media_items": [
            {
                "title": "Best clip ever",
                "external_media_id": "v1",
                "engagement_rate": 0.08,
                "published_at": "2026-07-01T18:00:00Z",
                "duration_seconds": 45,
                "media_kind": "short",
            },
            {
                "title": "Tutorial long",
                "external_media_id": "v2",
                "engagement_rate": 0.02,
                "published_at": "2026-06-20T12:00:00Z",
                "duration_seconds": 600,
                "media_kind": "video",
            },
        ],
        "last_synced_at": "2026-07-09T12:00:00Z",
    }
    result = analyze_competitor_snapshot(
        competitor_id=competitor_id,
        project_id=project_id,
        platform="youtube",
        handle="@rival",
        display_name="Rival",
        metrics=metrics,
    )
    assert result.score > 0
    assert result.patterns["subscriber_count"] == 50000
    assert result.patterns.get("shorts_ratio", 0) > 0
    assert any(rec.source == "competitor_analyzer" for rec in result.recommendations)


def test_analyze_competitor_requires_sync():
    with pytest.raises(ValueError, match="Sincronização"):
        analyze_competitor_snapshot(
            competitor_id=str(uuid4()),
            project_id=str(uuid4()),
            platform="youtube",
            handle="@x",
            display_name="X",
            metrics={"sync_error": "YOUTUBE_API_KEY not configured"},
        )


def test_analyze_competitor_requires_data():
    with pytest.raises(ValueError, match="Nenhum dado"):
        analyze_competitor_snapshot(
            competitor_id=str(uuid4()),
            project_id=str(uuid4()),
            platform="youtube",
            handle="@x",
            display_name="X",
            metrics={},
        )


def test_resolve_youtube_api_key_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert resolve_youtube_api_key() is None
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
    assert resolve_youtube_api_key() == "test-key"
