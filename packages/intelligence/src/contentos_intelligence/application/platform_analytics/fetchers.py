"""OAuth platform analytics fetchers — YouTube, TikTok, Instagram (V5.4.1)."""

from __future__ import annotations

from typing import Any

import httpx

from contentos_intelligence.application.platform_analytics.youtube import fetch_youtube_channel_data
from contentos_intelligence.domain.platform_metrics import PlatformMediaMetrics


def _engagement_rate(views: int, likes: int, comments: int, shares: int) -> float | None:
    if views <= 0:
        return None
    return round((likes + comments + shares) / views, 4)


async def fetch_youtube_analytics(credentials: dict[str, Any], *, limit: int = 10) -> tuple[list[PlatformMediaMetrics], dict[str, Any]]:
    return await fetch_youtube_channel_data(credentials, limit=limit)


async def fetch_tiktok_analytics(credentials: dict[str, Any], *, limit: int = 10) -> tuple[list[PlatformMediaMetrics], dict[str, Any]]:
    token = credentials.get("access_token")
    if not token:
        return [], {"error": "missing_access_token"}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    channel_totals: dict[str, Any] = {}
    items: list[PlatformMediaMetrics] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        user = await client.post(
            "https://open.tiktokapis.com/v2/user/info/",
            headers=headers,
            json={"fields": ["display_name", "follower_count", "following_count", "likes_count", "video_count"]},
        )
        if user.status_code == 403:
            return [], {"needs_reconnect": True, "error": "insufficient_scope"}
        if user.status_code < 400:
            u = user.json().get("data", {}).get("user", {})
            channel_totals = {
                "follower_count": u.get("follower_count"),
                "video_count": u.get("video_count"),
                "likes_count": u.get("likes_count"),
            }

        resp = await client.post(
            "https://open.tiktokapis.com/v2/video/list/",
            headers=headers,
            json={"max_count": min(limit, 20)},
            params={"fields": "id,title,view_count,like_count,comment_count,share_count,create_time"},
        )
        if resp.status_code >= 400:
            return items, {**channel_totals, "error": resp.text[:200]}
        for vid in resp.json().get("data", {}).get("videos", []):
            views = int(vid.get("view_count") or 0)
            likes = int(vid.get("like_count") or 0)
            comments = int(vid.get("comment_count") or 0)
            shares = int(vid.get("share_count") or 0)
            vid_id = vid.get("id")
            items.append(
                PlatformMediaMetrics(
                    platform="tiktok",
                    external_media_id=vid_id,
                    title=vid.get("title"),
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    engagement_rate=_engagement_rate(views, likes, comments, shares),
                    published_at=str(vid.get("create_time")) if vid.get("create_time") else None,
                )
            )
    return items, channel_totals


async def fetch_instagram_analytics(credentials: dict[str, Any], *, limit: int = 10) -> tuple[list[PlatformMediaMetrics], dict[str, Any]]:
    token = credentials.get("access_token")
    ig_user_id = credentials.get("instagram_user_id")
    if not token or not ig_user_id:
        return [], {"error": "missing_access_token_or_ig_user_id"}

    channel_totals: dict[str, Any] = {}
    items: list[PlatformMediaMetrics] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        profile = await client.get(
            f"https://graph.facebook.com/v19.0/{ig_user_id}",
            params={"fields": "followers_count,media_count,username", "access_token": token},
        )
        if profile.status_code == 403 or profile.status_code == 400:
            err = profile.json().get("error", {})
            if err.get("code") in (10, 200, 190):
                return [], {"needs_reconnect": True, "error": err.get("message", "insufficient_scope")}
        if profile.status_code < 400:
            p = profile.json()
            channel_totals = {
                "followers_count": p.get("followers_count"),
                "media_count": p.get("media_count"),
                "username": p.get("username"),
            }

        media = await client.get(
            f"https://graph.facebook.com/v19.0/{ig_user_id}/media",
            params={"fields": "id,caption,media_type,timestamp,permalink", "limit": min(limit, 25), "access_token": token},
        )
        if media.status_code >= 400:
            return items, {**channel_totals, "error": media.text[:200]}
        for m in media.json().get("data", []):
            media_id = m.get("id")
            insights_resp = await client.get(
                f"https://graph.facebook.com/v19.0/{media_id}/insights",
                params={
                    "metric": "impressions,reach,likes,comments,shares,saved",
                    "access_token": token,
                },
            )
            metrics_map: dict[str, int] = {}
            if insights_resp.status_code < 400:
                for row in insights_resp.json().get("data", []):
                    name = row.get("name")
                    values = row.get("values", [])
                    if name and values:
                        metrics_map[name] = int(values[0].get("value") or 0)
            views = metrics_map.get("impressions") or metrics_map.get("reach") or 0
            likes = metrics_map.get("likes", 0)
            comments = metrics_map.get("comments", 0)
            shares = metrics_map.get("shares", 0)
            items.append(
                PlatformMediaMetrics(
                    platform="instagram",
                    external_media_id=media_id,
                    title=(m.get("caption") or "")[:120] or None,
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    engagement_rate=_engagement_rate(views, likes, comments, shares),
                    published_at=m.get("timestamp"),
                    url=m.get("permalink"),
                )
            )
    return items, channel_totals


PLATFORM_FETCHERS = {
    "youtube": fetch_youtube_analytics,
    "tiktok": fetch_tiktok_analytics,
    "instagram": fetch_instagram_analytics,
}
