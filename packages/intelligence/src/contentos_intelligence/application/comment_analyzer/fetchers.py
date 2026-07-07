"""Fetch comments from OAuth-connected platforms — V5.4.3."""

from __future__ import annotations

from typing import Any

import httpx

from contentos_intelligence.domain.comment_analysis import CommentItem


async def fetch_youtube_comments(
    credentials: dict[str, Any],
    video_id: str,
    *,
    limit: int = 50,
) -> tuple[list[CommentItem], str | None]:
    token = credentials.get("access_token")
    if not token or not video_id:
        return [], "missing_token_or_video_id"
    headers = {"Authorization": f"Bearer {token}"}
    items: list[CommentItem] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            params={
                "part": "snippet",
                "videoId": video_id,
                "maxResults": min(limit, 100),
                "order": "relevance",
                "textFormat": "plainText",
            },
            headers=headers,
        )
        if resp.status_code == 403:
            return [], "insufficient_scope"
        if resp.status_code >= 400:
            return [], resp.text[:200]
        for thread in resp.json().get("items", []):
            snippet = thread.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            text = snippet.get("textDisplay") or snippet.get("textOriginal") or ""
            if not text.strip():
                continue
            items.append(
                CommentItem(
                    text=text.strip(),
                    author=snippet.get("authorDisplayName"),
                    platform="youtube",
                    external_media_id=video_id,
                    published_at=snippet.get("publishedAt"),
                )
            )
    return items, None


async def fetch_instagram_comments(
    credentials: dict[str, Any],
    media_id: str,
    *,
    limit: int = 50,
) -> tuple[list[CommentItem], str | None]:
    token = credentials.get("access_token")
    if not token or not media_id:
        return [], "missing_token_or_media_id"
    items: list[CommentItem] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"https://graph.facebook.com/v19.0/{media_id}/comments",
            params={
                "fields": "text,username,timestamp",
                "limit": min(limit, 50),
                "access_token": token,
            },
        )
        if resp.status_code == 403:
            return [], "insufficient_scope"
        if resp.status_code >= 400:
            return [], resp.text[:200]
        for row in resp.json().get("data", []):
            text = (row.get("text") or "").strip()
            if not text:
                continue
            items.append(
                CommentItem(
                    text=text,
                    author=row.get("username"),
                    platform="instagram",
                    external_media_id=media_id,
                    published_at=row.get("timestamp"),
                )
            )
    return items, None


async def fetch_tiktok_comments(
    credentials: dict[str, Any],
    video_id: str,
    *,
    limit: int = 50,
) -> tuple[list[CommentItem], str | None]:
    token = credentials.get("access_token")
    if not token or not video_id:
        return [], "missing_token_or_video_id"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://open.tiktokapis.com/v2/video/comment/list/",
            headers=headers,
            json={"video_id": video_id, "max_count": min(limit, 50)},
        )
        if resp.status_code in (403, 404, 501):
            return [], "comments_api_unavailable"
        if resp.status_code >= 400:
            return [], resp.text[:200]
        items: list[CommentItem] = []
        for row in resp.json().get("data", {}).get("comments", []):
            text = (row.get("text") or "").strip()
            if not text:
                continue
            items.append(
                CommentItem(
                    text=text,
                    author=row.get("username"),
                    platform="tiktok",
                    external_media_id=video_id,
                    published_at=str(row.get("create_time")) if row.get("create_time") else None,
                )
            )
        return items, None


COMMENT_FETCHERS = {
    "youtube": fetch_youtube_comments,
    "instagram": fetch_instagram_comments,
    "tiktok": fetch_tiktok_comments,
}
