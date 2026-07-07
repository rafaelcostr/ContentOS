"""Comment Analyzer service — V5.4.3."""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from contentos_intelligence.application.comment_analyzer.fetchers import COMMENT_FETCHERS
from contentos_intelligence.application.comment_analyzer.sentiment import analyze_comments
from contentos_intelligence.domain.comment_analysis import CommentAnalysisReport, CommentMediaAnalysis

try:
    from contentos_database.channel_credentials import credentials_connected
    from contentos_database.models import Channel, CommentAnalysisRow, PlatformAnalyticsSnapshot, Project
    from contentos_database.oauth_tokens import refresh_channel_token_if_needed
    from sqlalchemy import desc, select
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover
    AsyncSession = object  # type: ignore[misc, assignment]


def comment_analyzer_enabled() -> bool:
    return os.getenv("COMMENT_ANALYZER_ENABLED", "true").lower() in ("1", "true", "yes")


def comment_max_per_media() -> int:
    try:
        return max(5, min(100, int(os.getenv("COMMENT_ANALYZER_MAX_COMMENTS", "50"))))
    except ValueError:
        return 50


def auto_index_kb() -> bool:
    return os.getenv("COMMENT_ANALYZER_AUTO_INDEX_KB", "false").lower() in ("1", "true", "yes")


async def _load_media_targets(db: AsyncSession, project_id: UUID) -> list[PlatformAnalyticsSnapshot]:
    result = await db.execute(
        select(PlatformAnalyticsSnapshot)
        .where(
            PlatformAnalyticsSnapshot.project_id == project_id,
            PlatformAnalyticsSnapshot.external_media_id.isnot(None),
        )
        .order_by(desc(PlatformAnalyticsSnapshot.fetched_at))
        .limit(50)
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


async def _analyze_media(
    db: AsyncSession,
    snap: PlatformAnalyticsSnapshot,
    *,
    limit: int,
) -> CommentMediaAnalysis:
    platform = snap.platform.lower()
    media_id = snap.external_media_id or ""
    channel = await _channel_for_platform(db, snap.project_id, platform)
    if not channel:
        return CommentMediaAnalysis(
            platform=platform,
            external_media_id=media_id,
            title=snap.title,
            error="no_oauth_channel",
        )
    await refresh_channel_token_if_needed(channel)
    creds = dict(channel.credentials or {})
    fetcher = COMMENT_FETCHERS.get(platform)
    if not fetcher:
        return CommentMediaAnalysis(platform=platform, external_media_id=media_id, title=snap.title, error="unsupported_platform")

    comments, err = await fetcher(creds, media_id, limit=limit)
    analysis = analyze_comments(platform, media_id, snap.title, comments)
    if err:
        analysis.error = err
    return analysis


async def _index_to_kb(
    db: AsyncSession,
    project_id: UUID,
    org_id: UUID | None,
    analysis: CommentMediaAnalysis,
) -> int:
    if analysis.comment_count < 3 or not analysis.themes:
        return 0
    from contentos_database.models import KnowledgeEntry

    content = "\n".join(
        [
            f"Platform: {analysis.platform}",
            f"Title: {analysis.title or analysis.external_media_id}",
            f"Comments: {analysis.comment_count}",
            f"Sentiment: +{analysis.positive_pct}% / -{analysis.negative_pct}%",
            f"Themes: {', '.join(analysis.themes)}",
            "Samples:",
            *[f"- {s}" for s in analysis.sample_comments[:3]],
        ]
    )
    db.add(
        KnowledgeEntry(
            id=uuid.uuid4(),
            project_id=project_id,
            org_id=org_id,
            pipeline_id=None,
            resource_type="comments",
            resource_id=None,
            title=f"Comments [{analysis.platform}]: {analysis.title or analysis.external_media_id}"[:500],
            content_text=content,
            snippet=content[:400],
            metadata_={
                "source": "comment_analyzer",
                "platform": analysis.platform,
                "external_media_id": analysis.external_media_id,
                "themes": analysis.themes,
            },
            version=1,
        )
    )
    return 1


async def _persist_rows(db: AsyncSession, project_id: UUID, analyses: list[CommentMediaAnalysis], *, kb_indexed: bool) -> None:
    for a in analyses:
        db.add(
            CommentAnalysisRow(
                id=uuid.uuid4(),
                project_id=project_id,
                platform=a.platform,
                external_media_id=a.external_media_id,
                title=a.title,
                comment_count=a.comment_count,
                positive_pct=a.positive_pct,
                negative_pct=a.negative_pct,
                neutral_pct=a.neutral_pct,
                question_count=a.question_count,
                themes=a.themes,
                sample_comments=a.sample_comments,
                error=a.error,
                kb_indexed=kb_indexed and a.comment_count >= 3 and bool(a.themes),
            )
        )
    await db.flush()


async def analyze_project_comments(
    db: AsyncSession,
    project_id: UUID,
    *,
    persist: bool = True,
    index_kb: bool | None = None,
) -> CommentAnalysisReport:
    targets = await _load_media_targets(db, project_id)
    limit = comment_max_per_media()
    analyses: list[CommentMediaAnalysis] = []
    total = 0
    for snap in targets:
        analysis = await _analyze_media(db, snap, limit=limit)
        analyses.append(analysis)
        total += analysis.comment_count

    report = CommentAnalysisReport(project_id=str(project_id), media_analyses=analyses, total_comments=total)
    should_index = index_kb if index_kb is not None else auto_index_kb()
    kb_count = 0
    if should_index and persist:
        project = await db.get(Project, project_id)
        org_id = project.org_id if project else None
        for analysis in analyses:
            if not analysis.error:
                kb_count += await _index_to_kb(db, project_id, org_id, analysis)
    report.kb_indexed_count = kb_count

    if persist:
        await _persist_rows(db, project_id, analyses, kb_indexed=should_index)
    report.summary = (
        f"{len(analyses)} mídias · {total} comentários analisados · {kb_count} na KB"
        if analyses
        else "Nenhum snapshot OAuth com media_id — sincronize em /analytics primeiro."
    )
    return report


async def list_comment_insights(db: AsyncSession, project_id: UUID, *, limit: int = 50) -> list[dict[str, Any]]:
    result = await db.execute(
        select(CommentAnalysisRow)
        .where(CommentAnalysisRow.project_id == project_id)
        .order_by(desc(CommentAnalysisRow.created_at))
        .limit(min(limit, 200))
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "platform": r.platform,
            "external_media_id": r.external_media_id,
            "title": r.title,
            "comment_count": r.comment_count,
            "positive_pct": r.positive_pct,
            "negative_pct": r.negative_pct,
            "neutral_pct": r.neutral_pct,
            "question_count": r.question_count,
            "themes": r.themes or [],
            "sample_comments": r.sample_comments or [],
            "error": r.error,
            "kb_indexed": r.kb_indexed,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
