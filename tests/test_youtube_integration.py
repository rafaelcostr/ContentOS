"""YouTube integration tests — Growth OS Fase 3."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from contentos_intelligence.application.platform_analytics.youtube import (
    fetch_youtube_channel_data,
    parse_iso8601_duration,
)
from contentos_intelligence.domain.platform_metrics import PlatformMediaMetrics


def test_parse_iso8601_duration():
    assert parse_iso8601_duration("PT45S") == 45
    assert parse_iso8601_duration("PT1M30S") == 90
    assert parse_iso8601_duration("PT1H2M3S") == 3723
    assert parse_iso8601_duration("") == 0


@pytest.mark.asyncio
async def test_fetch_youtube_channel_data_missing_token():
    items, totals = await fetch_youtube_channel_data({})
    assert items == []
    assert totals["error"] == "missing_access_token"


@pytest.mark.asyncio
async def test_fetch_youtube_channel_data_full_flow():
    channel_payload = {
        "items": [
            {
                "id": "UC123",
                "snippet": {
                    "title": "My Channel",
                    "description": "About",
                    "customUrl": "@mychannel",
                    "thumbnails": {"high": {"url": "https://img.example/thumb.jpg"}},
                },
                "statistics": {
                    "subscriberCount": "1000",
                    "viewCount": "50000",
                    "videoCount": "12",
                },
                "brandingSettings": {"channel": {"keywords": "gaming"}},
                "contentDetails": {"relatedPlaylists": {"uploads": "UU123"}},
            }
        ]
    }
    playlists_payload = {
        "items": [
            {
                "id": "PL1",
                "snippet": {"title": "Highlights", "description": "Best", "publishedAt": "2026-01-01T00:00:00Z"},
                "contentDetails": {"itemCount": 3},
            }
        ]
    }
    playlist_items_payload = {
        "items": [
            {"contentDetails": {"videoId": "vid_short"}},
            {"contentDetails": {"videoId": "vid_long"}},
        ]
    }
    videos_payload = {
        "items": [
            {
                "id": "vid_short",
                "snippet": {"title": "Short clip", "publishedAt": "2026-02-01T00:00:00Z"},
                "statistics": {"viewCount": "100", "likeCount": "10", "commentCount": "2"},
                "contentDetails": {"duration": "PT30S"},
            },
            {
                "id": "vid_long",
                "snippet": {"title": "Long video", "publishedAt": "2026-01-15T00:00:00Z"},
                "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "8"},
                "contentDetails": {"duration": "PT10M5S"},
            },
        ]
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/channels") or "/channels?" in url:
            return httpx.Response(200, json=channel_payload)
        if "/playlists" in url and "playlistItems" not in url:
            return httpx.Response(200, json=playlists_payload)
        if "/playlistItems" in url:
            return httpx.Response(200, json=playlist_items_payload)
        if "/videos" in url:
            return httpx.Response(200, json=videos_payload)
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        items, totals = await fetch_youtube_channel_data({"access_token": "tok"}, limit=10, client=client)

    assert totals["youtube_channel_id"] == "UC123"
    assert totals["subscriber_count"] == 1000
    assert totals["shorts_count"] == 1
    assert totals["videos_count"] == 1
    assert len(totals["playlists"]) == 1
    assert len(items) == 2
    kinds = {item.media_kind for item in items}
    assert kinds == {"short", "video"}


def test_platform_media_metrics_includes_media_kind():
    item = PlatformMediaMetrics(platform="youtube", media_kind="short", duration_seconds=30)
    restored = PlatformMediaMetrics.from_dict(item.to_dict())
    assert restored.media_kind == "short"
    assert restored.duration_seconds == 30


@pytest.mark.asyncio
async def test_build_youtube_connection_status():
    from contentos_intelligence.application.platform_analytics.service import build_youtube_connection_status

    channel = MagicMock()
    channel.id = "00000000-0000-0000-0000-000000000001"
    channel.project_id = "00000000-0000-0000-0000-000000000002"
    channel.platform = "youtube"
    channel.name = "YT"
    channel.is_active = True
    channel.credentials = {
        "access_token": "abc",
        "refresh_token": "ref",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "youtube_channel_id": "UC123",
    }

    status = build_youtube_connection_status(channel)
    assert status["oauth_connected"] is True
    assert status["has_refresh_token"] is True
    assert status["youtube_channel_id"] == "UC123"
