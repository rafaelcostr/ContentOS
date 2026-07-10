"""YouTube Data API integration — channel, videos, Shorts, playlists (Growth OS Fase 3)."""

from __future__ import annotations

import re
from typing import Any

import httpx

from contentos_intelligence.domain.platform_metrics import PlatformMediaMetrics

_YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
_SHORT_MAX_SECONDS = 60


def parse_iso8601_duration(duration: str | None) -> int:
    if not duration:
        return 0
    match = re.match(
        r"^PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$",
        duration,
    )
    if not match:
        return 0
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return hours * 3600 + minutes * 60 + seconds


def _engagement_rate(views: int, likes: int, comments: int, shares: int) -> float | None:
    if views <= 0:
        return None
    return round((likes + comments + shares) / views, 4)


def _media_from_video(vid: dict[str, Any]) -> PlatformMediaMetrics:
    stats = vid.get("statistics", {})
    snippet = vid.get("snippet", {})
    content = vid.get("contentDetails", {})
    duration_seconds = parse_iso8601_duration(content.get("duration"))
    vid_id = vid.get("id")
    views = int(stats.get("viewCount") or 0)
    likes = int(stats.get("likeCount") or 0)
    comments = int(stats.get("commentCount") or 0)
    media_kind = "short" if 0 < duration_seconds <= _SHORT_MAX_SECONDS else "video"
    return PlatformMediaMetrics(
        platform="youtube",
        external_media_id=vid_id,
        title=snippet.get("title"),
        views=views,
        likes=likes,
        comments=comments,
        shares=0,
        engagement_rate=_engagement_rate(views, likes, comments, 0),
        published_at=snippet.get("publishedAt"),
        url=f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None,
        media_kind=media_kind,
        duration_seconds=duration_seconds,
    )


async def fetch_youtube_channel_data(
    credentials: dict[str, Any],
    *,
    limit: int = 10,
    client: httpx.AsyncClient | None = None,
) -> tuple[list[PlatformMediaMetrics], dict[str, Any]]:
    token = credentials.get("access_token")
    if not token:
        return [], {"error": "missing_access_token"}

    headers = {"Authorization": f"Bearer {token}"}
    channel_totals: dict[str, Any] = {}
    items: list[PlatformMediaMetrics] = []
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=30.0)

    try:
        ch = await http.get(
            f"{_YOUTUBE_API}/channels",
            params={
                "part": "snippet,statistics,brandingSettings,contentDetails",
                "mine": "true",
            },
            headers=headers,
        )
        if ch.status_code == 403:
            return [], {"needs_reconnect": True, "error": "insufficient_scope"}
        if ch.status_code >= 400:
            return [], {"error": ch.text[:200]}

        ch_items = ch.json().get("items", [])
        if not ch_items:
            return [], {"error": "no_youtube_channel_found"}

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
            "country": snippet.get("country"),
            "thumbnail_url": thumb.get("url"),
            "keywords": branding.get("keywords"),
            "subscriber_count": int(stats.get("subscriberCount") or 0),
            "view_count": int(stats.get("viewCount") or 0),
            "video_count": int(stats.get("videoCount") or 0),
            "hidden_subscriber_count": stats.get("hiddenSubscriberCount") is True,
            "uploads_playlist_id": content_details.get("uploads"),
            "playlists": [],
            "shorts_count": 0,
            "videos_count": 0,
        }

        playlists_resp = await http.get(
            f"{_YOUTUBE_API}/playlists",
            params={
                "part": "snippet,contentDetails",
                "mine": "true",
                "maxResults": min(25, max(limit, 10)),
            },
            headers=headers,
        )
        if playlists_resp.status_code < 400:
            channel_totals["playlists"] = [
                {
                    "id": row.get("id"),
                    "title": row.get("snippet", {}).get("title"),
                    "description": row.get("snippet", {}).get("description"),
                    "item_count": int(row.get("contentDetails", {}).get("itemCount") or 0),
                    "published_at": row.get("snippet", {}).get("publishedAt"),
                }
                for row in playlists_resp.json().get("items", [])
            ]

        uploads_playlist_id = content_details.get("uploads")
        video_ids: list[str] = []
        if uploads_playlist_id:
            playlist_items = await http.get(
                f"{_YOUTUBE_API}/playlistItems",
                params={
                    "part": "contentDetails",
                    "playlistId": uploads_playlist_id,
                    "maxResults": min(limit, 25),
                },
                headers=headers,
            )
            if playlist_items.status_code < 400:
                video_ids = [
                    item.get("contentDetails", {}).get("videoId")
                    for item in playlist_items.json().get("items", [])
                    if item.get("contentDetails", {}).get("videoId")
                ]

        if not video_ids:
            search = await http.get(
                f"{_YOUTUBE_API}/search",
                params={
                    "part": "id",
                    "forMine": "true",
                    "type": "video",
                    "maxResults": min(limit, 25),
                    "order": "date",
                },
                headers=headers,
            )
            if search.status_code < 400:
                video_ids = [
                    item["id"]["videoId"]
                    for item in search.json().get("items", [])
                    if item.get("id", {}).get("videoId")
                ]

        if video_ids:
            videos = await http.get(
                f"{_YOUTUBE_API}/videos",
                params={
                    "part": "statistics,snippet,contentDetails",
                    "id": ",".join(video_ids),
                },
                headers=headers,
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


async def fetch_youtube_analytics(credentials: dict[str, Any], *, limit: int = 10) -> tuple[list[PlatformMediaMetrics], dict[str, Any]]:
    """Backward-compatible entry point used by PLATFORM_FETCHERS."""
    return await fetch_youtube_channel_data(credentials, limit=limit)
