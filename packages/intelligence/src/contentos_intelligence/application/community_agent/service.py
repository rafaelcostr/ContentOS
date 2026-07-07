"""Community Agent service — draft replies only (V5.4.4)."""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from contentos_intelligence.application.comment_analyzer.fetchers import COMMENT_FETCHERS
from contentos_intelligence.application.community_agent.drafter import (
    draft_reply_for_comment,
    select_comments_for_drafts,
)
from contentos_intelligence.domain.community_draft import CommentReplyDraft, CommunityDraftReport

try:
    from contentos_database.channel_credentials import credentials_connected
    from contentos_database.models import Channel, CommunityReplyDraftRow, PlatformAnalyticsSnapshot
    from contentos_database.oauth_tokens import refresh_channel_token_if_needed
    from sqlalchemy import desc, select
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover
    AsyncSession = object  # type: ignore[misc, assignment]


def community_agent_enabled() -> bool:
    return os.getenv("COMMUNITY_AGENT_ENABLED", "true").lower() in ("1", "true", "yes")


def community_auto_post() -> bool:
    """Always false in V5.4.4 — drafts only."""
    return False


def community_drafts_max() -> int:
    try:
        return max(1, min(50, int(os.getenv("COMMUNITY_DRAFTS_MAX", "20"))))
    except ValueError:
        return 20


async def _load_media_targets(db: AsyncSession, project_id: UUID) -> list[PlatformAnalyticsSnapshot]:
    result = await db.execute(
        select(PlatformAnalyticsSnapshot)
        .where(
            PlatformAnalyticsSnapshot.project_id == project_id,
            PlatformAnalyticsSnapshot.external_media_id.isnot(None),
        )
        .order_by(desc(PlatformAnalyticsSnapshot.fetched_at))
        .limit(20)
    )
    rows = list(result.scalars().all())
    seen: set[tuple[str, str]] = set()
    unique: list[PlatformAnalyticsSnapshot] = []
    for row in rows:
        if not row.external_media_id:
            continue
        key = (row.platform, row.external_media_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


async def _channel_for_platform(db: AsyncSession, project_id: UUID, platform: str) -> Channel | None:
    result = await db.execute(
        select(Channel)
        .where(Channel.project_id == project_id, Channel.platform == platform, Channel.is_active.is_(True))
        .order_by(desc(Channel.created_at))
        .limit(1)
    )
    channel = result.scalar_one_or_none()
    if channel and credentials_connected(channel.credentials):
        return channel
    return None


def _topic_from_snap(snap: PlatformAnalyticsSnapshot) -> str:
    title = (snap.title or "").strip()
    if title:
        return title.split("—")[0].split("#")[0].strip()
    return ""


async def generate_community_drafts(
    db: AsyncSession,
    project_id: UUID,
    *,
    persist: bool = True,
    max_drafts: int | None = None,
) -> CommunityDraftReport:
    if community_auto_post():
        raise RuntimeError("COMMUNITY_AUTO_POST is disabled in V5.4.4")

    limit = max_drafts or community_drafts_max()
    targets = await _load_media_targets(db, project_id)
    all_drafts: list[CommentReplyDraft] = []

    for snap in targets:
        platform = snap.platform.lower()
        media_id = snap.external_media_id or ""
        channel = await _channel_for_platform(db, snap.project_id, platform)
        if not channel:
            continue
        await refresh_channel_token_if_needed(channel)
        fetcher = COMMENT_FETCHERS.get(platform)
        if not fetcher:
            continue
        comments, err = await fetcher(dict(channel.credentials or {}), media_id, limit=50)
        if err or not comments:
            continue
        topic = _topic_from_snap(snap)
        selected = select_comments_for_drafts(comments, max_drafts=min(limit, 10))
        for comment in selected:
            all_drafts.append(
                draft_reply_for_comment(
                    comment,
                    platform=platform,
                    external_media_id=media_id,
                    media_title=snap.title,
                    topic=topic,
                )
            )

    all_drafts.sort(key=lambda d: -d.priority)
    all_drafts = all_drafts[:limit]

    if persist and all_drafts:
        for draft in all_drafts:
            row_id = uuid.uuid4()
            db.add(
                CommunityReplyDraftRow(
                    id=row_id,
                    project_id=project_id,
                    platform=draft.platform,
                    external_media_id=draft.external_media_id,
                    media_title=draft.media_title,
                    original_comment=draft.original_comment,
                    comment_author=draft.comment_author,
                    draft_reply=draft.draft_reply,
                    category=draft.category,
                    sentiment=draft.sentiment,
                    priority=draft.priority,
                    status="draft",
                )
            )
            draft.draft_id = str(row_id)
        await db.flush()

    report = CommunityDraftReport(
        project_id=str(project_id),
        drafts=all_drafts,
        drafts_created=len(all_drafts),
        auto_post=False,
        summary=(
            f"{len(all_drafts)} rascunhos gerados (sem publicação automática)"
            if all_drafts
            else "Nenhum comentário OAuth disponível — sincronize /analytics e analise comentários primeiro."
        ),
    )
    return report


async def list_community_drafts(
    db: AsyncSession,
    project_id: UUID,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    query = (
        select(CommunityReplyDraftRow)
        .where(CommunityReplyDraftRow.project_id == project_id)
        .order_by(desc(CommunityReplyDraftRow.priority), desc(CommunityReplyDraftRow.created_at))
        .limit(min(limit, 200))
    )
    if status:
        query = query.where(CommunityReplyDraftRow.status == status)
    rows = (await db.execute(query)).scalars().all()
    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "platform": r.platform,
            "external_media_id": r.external_media_id,
            "media_title": r.media_title,
            "original_comment": r.original_comment,
            "comment_author": r.comment_author,
            "draft_reply": r.draft_reply,
            "category": r.category,
            "sentiment": r.sentiment,
            "priority": r.priority,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


async def update_draft_status(
    db: AsyncSession,
    draft_id: UUID,
    *,
    status: str,
) -> dict[str, Any] | None:
    if status not in ("draft", "approved", "dismissed"):
        raise ValueError(f"Invalid status: {status}")
    row = await db.get(CommunityReplyDraftRow, draft_id)
    if not row:
        return None
    row.status = status
    await db.flush()
    return {
        "id": str(row.id),
        "status": row.status,
        "draft_reply": row.draft_reply,
        "auto_post": False,
    }
