"""Performance Learning — OAuth metrics + retention → KB/Memory (V5.4.2)."""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from contentos_intelligence.application.performance_learning.scoring import (
    build_learnings,
    classify_tier,
    compute_ctr,
    match_retention,
    topic_from_title,
)
from contentos_intelligence.domain.performance_learning import PerformanceLearningReport, PerformanceMediaInsight
from contentos_intelligence.domain.retention_report import RetentionReport

try:
    from contentos_database.models import (
        Job,
        JobStatus,
        LearningInsightRow,
        PerformanceLearningRow,
        Pipeline,
        PlatformAnalyticsSnapshot,
        Project,
    )
    from sqlalchemy import desc, select
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover
    AsyncSession = object  # type: ignore[misc, assignment]


def performance_learning_enabled() -> bool:
    return os.getenv("PERFORMANCE_LEARNING_ENABLED", "true").lower() in ("1", "true", "yes")


def auto_index_kb() -> bool:
    return os.getenv("PERFORMANCE_LEARNING_AUTO_INDEX_KB", "true").lower() in ("1", "true", "yes")


def auto_apply_memory() -> bool:
    return os.getenv("PERFORMANCE_LEARNING_AUTO_MEMORY", "true").lower() in ("1", "true", "yes")


def _snippet(text: str, max_len: int = 400) -> str:
    t = (text or "").strip()
    return t if len(t) <= max_len else t[: max_len - 3] + "..."


async def _load_latest_snapshots(db: AsyncSession, project_id: UUID) -> list[PlatformAnalyticsSnapshot]:
    result = await db.execute(
        select(PlatformAnalyticsSnapshot)
        .where(PlatformAnalyticsSnapshot.project_id == project_id)
        .order_by(desc(PlatformAnalyticsSnapshot.fetched_at))
        .limit(200)
    )
    rows = list(result.scalars().all())
    seen: set[tuple[str, str | None]] = set()
    unique: list[PlatformAnalyticsSnapshot] = []
    for row in rows:
        key = (row.platform, row.external_media_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


async def _load_retention_by_topic(db: AsyncSession, project_id: UUID) -> dict[str, dict[str, Any]]:
    result = await db.execute(
        select(Job, Pipeline)
        .join(Pipeline, Job.pipeline_id == Pipeline.id)
        .where(
            Pipeline.project_id == project_id,
            Job.step == "retention",
            Job.status == JobStatus.COMPLETED,
            Job.output_data.isnot(None),
        )
        .order_by(desc(Job.finished_at))
        .limit(100)
    )
    by_topic: dict[str, dict[str, Any]] = {}
    for job, pipeline in result.all():
        output = job.output_data or {}
        report_data = output.get("retention_report") or output
        report = RetentionReport.from_dict(report_data if isinstance(report_data, dict) else {})
        topic = (pipeline.topic or "").strip().lower()
        if not topic or topic in by_topic:
            continue
        by_topic[topic] = {
            "pipeline_id": str(pipeline.id),
            "completion_pct": report.completion_pct,
            "hook_retention_pct": report.hook_retention_pct,
            "avg_retention_pct": report.avg_retention_pct,
        }
    return by_topic


async def _load_hooks_by_topic(db: AsyncSession, project_id: UUID) -> dict[str, str]:
    result = await db.execute(
        select(LearningInsightRow)
        .where(LearningInsightRow.project_id == project_id)
        .order_by(desc(LearningInsightRow.created_at))
        .limit(100)
    )
    hooks: dict[str, str] = {}
    for row in result.scalars().all():
        topic = (row.topic or "").strip().lower()
        if topic and row.hook_text and topic not in hooks:
            hooks[topic] = row.hook_text
    return hooks


def _insight_from_snapshot(
    snap: PlatformAnalyticsSnapshot,
    retention_by_topic: dict[str, dict[str, Any]],
    hooks_by_topic: dict[str, str],
) -> PerformanceMediaInsight:
    metrics = dict(snap.metrics or {})
    views = int(metrics.get("views") or 0)
    ctr = compute_ctr(metrics)
    topic = topic_from_title(snap.title)
    retention_match = match_retention(snap.title, retention_by_topic)
    retention_pct = None
    predicted_pct = None
    retention_delta = None
    pipeline_id = None
    hook_text = hooks_by_topic.get(topic.lower()) if topic else None

    if retention_match:
        retention_pct = float(retention_match.get("completion_pct") or retention_match.get("avg_retention_pct") or 0)
        predicted_pct = float(retention_match.get("hook_retention_pct") or 0) or None
        pipeline_id = retention_match.get("pipeline_id")
        if predicted_pct is not None:
            retention_delta = round(retention_pct - predicted_pct, 2)
        if not hook_text and pipeline_id:
            for t, h in hooks_by_topic.items():
                if t in topic.lower() or topic.lower() in t:
                    hook_text = h
                    break

    tier = classify_tier(ctr=ctr, views=views, retention_pct=retention_pct)
    insight = PerformanceMediaInsight(
        platform=snap.platform,
        external_media_id=snap.external_media_id,
        title=snap.title,
        topic=topic or (snap.title or ""),
        views=views,
        likes=int(metrics.get("likes") or 0),
        comments=int(metrics.get("comments") or 0),
        shares=int(metrics.get("shares") or 0),
        ctr=ctr,
        engagement_rate=metrics.get("engagement_rate"),
        retention_pct=retention_pct,
        predicted_retention_pct=predicted_pct,
        retention_delta=retention_delta,
        performance_tier=tier,
        pipeline_id=pipeline_id,
        hook_text=hook_text,
    )
    insight.learnings = build_learnings(insight)
    return insight


async def _index_insight_to_kb(
    db: AsyncSession,
    project_id: UUID,
    org_id: UUID | None,
    insight: PerformanceMediaInsight,
) -> int:
    from contentos_database.models import KnowledgeEntry

    if insight.performance_tier != "high" or not insight.learnings:
        return 0
    body_lines = [
        f"Platform: {insight.platform}",
        f"Title: {insight.title or insight.topic}",
        f"Views: {insight.views} · CTR: {insight.ctr or 0:.2%}",
    ]
    if insight.retention_pct is not None:
        body_lines.append(f"Retention: {insight.retention_pct:.1f}% (delta {insight.retention_delta or 0:+.1f} p.p.)")
    if insight.hook_text:
        body_lines.append(f"Hook: {insight.hook_text}")
    body_lines.extend(insight.learnings)
    content = "\n".join(body_lines)
    db.add(
        KnowledgeEntry(
            id=uuid.uuid4(),
            project_id=project_id,
            org_id=org_id,
            pipeline_id=UUID(insight.pipeline_id) if insight.pipeline_id else None,
            resource_type="performance",
            resource_id=None,
            title=f"Performance [{insight.platform}]: {insight.title or insight.topic}"[:500],
            content_text=content,
            snippet=_snippet(content),
            metadata_={
                "source": "performance_learning",
                "platform": insight.platform,
                "external_media_id": insight.external_media_id,
                "ctr": insight.ctr,
                "retention_pct": insight.retention_pct,
                "retention_delta": insight.retention_delta,
                "tier": insight.performance_tier,
            },
            version=1,
        )
    )
    return 1


async def _apply_top_hooks_to_memory(project_id: UUID, top: list[PerformanceMediaInsight]) -> list[str]:
    if not auto_apply_memory() or not top:
        return []
    try:
        from contentos_memory.infrastructure.db_repository import load_sync, upsert_sync

        memory = load_sync(project_id)
        updates: list[str] = []
        for insight in top[:3]:
            if not insight.hook_text:
                continue
            if insight.hook_text not in memory.hook_patterns:
                memory.hook_patterns = [insight.hook_text, *(memory.hook_patterns or [])][:12]
                updates.append("hook_patterns")
        if updates:
            upsert_sync(memory)
        return updates
    except Exception:
        return []


async def _persist_insight_rows(
    db: AsyncSession,
    project_id: UUID,
    insights: list[PerformanceMediaInsight],
    *,
    kb_indexed: bool,
) -> None:
    for insight in insights:
        db.add(
            PerformanceLearningRow(
                id=uuid.uuid4(),
                project_id=project_id,
                platform=insight.platform,
                external_media_id=insight.external_media_id,
                pipeline_id=UUID(insight.pipeline_id) if insight.pipeline_id else None,
                title=insight.title,
                topic=insight.topic,
                ctr=insight.ctr,
                engagement_rate=insight.engagement_rate,
                retention_pct=insight.retention_pct,
                retention_delta=insight.retention_delta,
                views=insight.views,
                likes=insight.likes,
                comments=insight.comments,
                performance_tier=insight.performance_tier,
                learnings=insight.learnings,
                kb_indexed=kb_indexed and insight.performance_tier == "high",
            )
        )
    await db.flush()


async def process_project_performance_learning(
    db: AsyncSession,
    project_id: UUID,
    *,
    persist: bool = True,
    index_kb: bool | None = None,
) -> PerformanceLearningReport:
    snapshots = await _load_latest_snapshots(db, project_id)
    retention_by_topic = await _load_retention_by_topic(db, project_id)
    hooks_by_topic = await _load_hooks_by_topic(db, project_id)

    insights = [_insight_from_snapshot(s, retention_by_topic, hooks_by_topic) for s in snapshots]
    top = [i for i in insights if i.performance_tier == "high"]
    top.sort(key=lambda x: (x.ctr or 0, x.views), reverse=True)

    report = PerformanceLearningReport(
        project_id=str(project_id),
        media_insights=insights,
        top_performers=top[:10],
    )

    should_index = index_kb if index_kb is not None else auto_index_kb()
    kb_count = 0
    if should_index and persist:
        project = await db.get(Project, project_id)
        org_id = project.org_id if project else None
        for insight in top:
            kb_count += await _index_insight_to_kb(db, project_id, org_id, insight)
    report.kb_indexed_count = kb_count

    if persist:
        await _persist_insight_rows(db, project_id, insights, kb_indexed=should_index)
        memory_updates = await _apply_top_hooks_to_memory(project_id, top)
        report.memory_applied = bool(memory_updates)
        report.memory_updates = memory_updates

    high_n = len(top)
    report.summary = (
        f"{len(insights)} mídias analisadas · {high_n} alto desempenho · {kb_count} entradas na KB"
        if insights
        else "Nenhum snapshot OAuth — execute sync em /analytics primeiro."
    )
    return report


async def list_performance_insights(
    db: AsyncSession,
    project_id: UUID,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(PerformanceLearningRow)
        .where(PerformanceLearningRow.project_id == project_id)
        .order_by(desc(PerformanceLearningRow.created_at))
        .limit(min(limit, 200))
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "platform": r.platform,
            "external_media_id": r.external_media_id,
            "pipeline_id": str(r.pipeline_id) if r.pipeline_id else None,
            "title": r.title,
            "topic": r.topic,
            "ctr": r.ctr,
            "engagement_rate": r.engagement_rate,
            "retention_pct": r.retention_pct,
            "retention_delta": r.retention_delta,
            "views": r.views,
            "likes": r.likes,
            "comments": r.comments,
            "performance_tier": r.performance_tier,
            "learnings": r.learnings or [],
            "kb_indexed": r.kb_indexed,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
