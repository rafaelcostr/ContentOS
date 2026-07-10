"""YouTube public channel fetch — competitor intelligence (API key, no OAuth)."""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from contentos_intelligence.application.platform_analytics.youtube import (
    _YOUTUBE_API,
    _media_from_video,
)
from contentos_intelligence.domain.platform_metrics import PlatformMediaMetrics

_CHANNEL_ID_RE = re.compile(r"^UC[\w-]{20,}$")


def resolve_youtube_api_key() -> str | None:
    return os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")


def normalize_youtube_ref(handle_or_url: str) -> tuple[str, str]:
    """Return (kind, value) where kind is 'handle' or 'id'."""
    text = (handle_or_url or "").strip()
    if not text:
        return "handle", ""

    if text.startswith("http"):
        path = urlparse(text).path.strip("/")
        parts = path.split("/")
        if parts and parts[0].startswith("@"):
            return "handle", parts[0][1:]
        if "channel" in parts:
            idx = parts.index("channel")
            if idx + 1 < len(parts) and _CHANNEL_ID_RE.match(parts[idx + 1]):
                return "id", parts[idx + 1]
        if parts and _CHANNEL_ID_RE.match(parts[-1]):
            return "id", parts[-1]

    if text.startswith("@"):
        return "handle", text[1:]
    if _CHANNEL_ID_RE.match(text):
        return "id", text
    return "handle", text.lstrip("@")


async def fetch_youtube_public_channel(
    handle_or_url: str,
    *,
    api_key: str,
    limit: int = 10,
    client: httpx.AsyncClient | None = None,
) -> tuple[list[PlatformMediaMetrics], dict[str, Any]]:
    kind, value = normalize_youtube_ref(handle_or_url)
    if not value:
        return [], {"error": "invalid_youtube_handle"}

    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=30.0)
    channel_totals: dict[str, Any] = {}
    items: list[PlatformMediaMetrics] = []

    try:
        params: dict[str, Any] = {
            "part": "snippet,statistics,contentDetails,brandingSettings",
            "key": api_key,
        }
        if kind == "id":
            params["id"] = value
        else:
            params["forHandle"] = value

        ch = await http.get(f"{_YOUTUBE_API}/channels", params=params)
        if ch.status_code == 403:
            return [], {"error": "youtube_api_forbidden", "detail": ch.text[:200]}
        if ch.status_code >= 400:
            return [], {"error": "youtube_api_error", "detail": ch.text[:200]}

        ch_items = ch.json().get("items", [])
        if not ch_items and kind == "handle":
            search = await http.get(
                f"{_YOUTUBE_API}/search",
                params={
                    "part": "snippet",
                    "type": "channel",
                    "q": value,
                    "maxResults": 1,
                    "key": api_key,
                },
            )
            if search.status_code < 400:
                search_items = search.json().get("items", [])
                if search_items:
                    channel_id = search_items[0].get("snippet", {}).get("channelId")
                    if channel_id:
                        ch = await http.get(
                            f"{_YOUTUBE_API}/channels",
                            params={
                                "part": "snippet,statistics,contentDetails,brandingSettings",
                                "id": channel_id,
                                "key": api_key,
                            },
                        )
                        ch_items = ch.json().get("items", [])

        if not ch_items:
            return [], {"error": "youtube_channel_not_found"}

        channel = ch_items[0]
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})
        branding = channel.get("brandingSettings", {}).get("channel", {})
        content_details = channel.get("contentDetails", {}).get("relatedPlaylists", {})
        youtube_channel_id = channel.get("id")
        thumbnails = snippet.get("thumbnails", {})
        thumb = thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}

        channel_totals = {
            "youtube_channel_id": youtube_channel_id,
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "custom_url": snippet.get("customUrl"),
            "thumbnail_url": thumb.get("url"),
            "keywords": branding.get("keywords"),
            "subscriber_count": int(stats.get("subscriberCount") or 0),
            "view_count": int(stats.get("viewCount") or 0),
            "video_count": int(stats.get("videoCount") or 0),
            "shorts_count": 0,
            "videos_count": 0,
        }

        uploads_playlist_id = content_details.get("uploads")
        video_ids: list[str] = []
        if uploads_playlist_id:
            playlist_items = await http.get(
                f"{_YOUTUBE_API}/playlistItems",
                params={
                    "part": "contentDetails",
                    "playlistId": uploads_playlist_id,
                    "maxResults": min(limit, 25),
                    "key": api_key,
                },
            )
            if playlist_items.status_code < 400:
                video_ids = [
                    item.get("contentDetails", {}).get("videoId")
                    for item in playlist_items.json().get("items", [])
                    if item.get("contentDetails", {}).get("videoId")
                ]

        if video_ids:
            videos = await http.get(
                f"{_YOUTUBE_API}/videos",
                params={
                    "part": "statistics,snippet,contentDetails",
                    "id": ",".join(video_ids),
                    "key": api_key,
                },
            )
            if videos.status_code < 400:
                for vid in videos.json().get("items", []):
                    media = _media_from_video(vid)
                    items.append(media)
                    if media.media_kind == "short":
                        channel_totals["shorts_count"] += 1
                    else:
                        channel_totals["videos_count"] += 1

        return items, channel_totals
    finally:
        if owns_client:
            await http.aclose()
