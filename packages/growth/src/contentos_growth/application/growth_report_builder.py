"""Growth Report builder — consolidates module signals (Growth OS Fase 8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import mean
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_growth.application.performance_learning_interpreter import (
    PerformanceInterpretation,
    interpret_performance_insights,
)
from contentos_growth.application.platform_analytics_aggregator import enrich_channel_health
from contentos_growth.domain import (
    ChannelProfile,
    CompetitorProfile,
    GrowthRecommendation,
    GrowthReport,
    GrowthStrategy,
)

_CONFIDENCE_TO_PRIORITY = {"high": "high", "medium": "medium", "low": "low"}


@dataclass
class GrowthReportSignals:
    memory_niche: str = ""
    memory_mission: str = ""
    memory_goal: str = ""
    analytics_summary: dict[str, Any] = field(default_factory=dict)
    learning_rows: list[dict[str, Any]] = field(default_factory=list)
    perf_rows: list[dict[str, Any]] = field(default_factory=list)
    analytics_insights: list[dict[str, Any]] = field(default_factory=list)
    publish_stats: dict[str, Any] = field(default_factory=dict)
    quality_stats: dict[str, Any] = field(default_factory=dict)
    asset_count: int = 0
    content_rec_summary: str = ""
    content_recommendations: list[dict[str, Any]] = field(default_factory=list)


async def gather_growth_report_signals(db: AsyncSession, project_id: UUID) -> GrowthReportSignals:
    """Read-only aggregation from existing modules — no rewrites."""
    signals = GrowthReportSignals()

    try:
        from contentos_memory import get_memory_service

        memory = await get_memory_service().get_async(db, project_id)
        signals.memory_niche = memory.niche or ""
        signals.memory_mission = memory.mission or ""
        signals.memory_goal = memory.goal or ""
    except Exception:
        pass

    try:
        from contentos_intelligence.application.platform_analytics import (
            list_recent_snapshots,
            summarize_snapshots,
        )

        snapshots = await list_recent_snapshots(db, project_id, limit=100)
        signals.analytics_summary = summarize_snapshots(snapshots)
    except Exception:
        pass

    try:
        from contentos_intelligence.application.performance_learning import list_performance_insights

        signals.perf_rows = await list_performance_insights(db, project_id, limit=30)
    except Exception:
        pass

    try:
        from contentos_intelligence.infrastructure.learning_repository import LearningRepository

        signals.learning_rows = await LearningRepository().list_by_project(db, project_id, limit=20)
    except Exception:
        pass

    try:
        from contentos_analytics_ai.infrastructure.db_repository import InsightRepository

        signals.analytics_insights = await InsightRepository().list_by_project(db, project_id, limit=10)
    except Exception:
        pass

    try:
        from contentos_database.models import PlatformPublicationRow

        rows = (
            await db.execute(
                select(PlatformPublicationRow)
                .where(PlatformPublicationRow.project_id == project_id)
                .order_by(desc(PlatformPublicationRow.created_at))
                .limit(50)
            )
        ).scalars().all()
        success = sum(1 for row in rows if (row.status or "").lower() in {"success", "published", "live"})
        failed = sum(1 for row in rows if (row.status or "").lower() in {"failed", "error"})
        signals.publish_stats = {
            "attempts": len(rows),
            "success": success,
            "failed": failed,
        }
    except Exception:
        pass

    try:
        from contentos_database.models import Job, Pipeline
        from contentos_shared.enums import JobStatus

        rows = (
            await db.execute(
                select(Job)
                .join(Pipeline, Pipeline.id == Job.pipeline_id)
                .where(
                    Pipeline.project_id == project_id,
                    Job.step == "quality",
                    Job.status == JobStatus.COMPLETED.value,
                )
                .order_by(desc(Job.finished_at))
                .limit(20)
            )
        ).scalars().all()
        scores: list[float] = []
        passed = 0
        for job in rows:
            output = job.output_data or {}
            if output.get("quality_score") is not None:
                scores.append(float(output["quality_score"]))
            if output.get("quality_passed") is True:
                passed += 1
        signals.quality_stats = {
            "samples": len(rows),
            "avg_score": round(mean(scores), 2) if scores else None,
            "pass_rate": round(passed / len(rows), 2) if rows else None,
        }
    except Exception:
        pass

    try:
        from contentos_database.models import Asset

        count = (
            await db.execute(
                select(func.count()).select_from(Asset).where(Asset.project_id == project_id)
            )
        ).scalar_one()
        signals.asset_count = int(count or 0)
    except Exception:
        pass

    try:
        from contentos_intelligence.application.recommendations import build_project_recommendations

        content_report = await build_project_recommendations(db, project_id)
        signals.content_rec_summary = content_report.summary
        signals.content_recommendations = [rec.to_dict() for rec in content_report.recommendations]
    except Exception:
        pass

    return signals


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def compute_growth_score(
    *,
    channels: list[ChannelProfile],
    competitors: list[CompetitorProfile],
    signals: GrowthReportSignals,
) -> float:
    score = 25.0
    if channels:
        avg_channel = mean(ch.score for ch in channels if ch.score) if any(ch.score for ch in channels) else 0
        score += min(avg_channel * 0.2, 20.0)
        score += min(len(channels) * 4.0, 12.0)
    score += min(len(competitors) * 5.0, 15.0)
    if signals.analytics_summary.get("snapshot_count"):
        score += min(float(signals.analytics_summary["snapshot_count"]) * 0.5, 10.0)
    learning_scores = [float(r["content_score"]) for r in signals.learning_rows if r.get("content_score") is not None]
    if learning_scores:
        score += min(mean(learning_scores) * 0.08, 10.0)
    if signals.perf_rows:
        score += min(len(signals.perf_rows) * 0.5, 8.0)
    if signals.quality_stats.get("pass_rate") is not None:
        score += float(signals.quality_stats["pass_rate"]) * 5.0
    if signals.publish_stats.get("success"):
        score += min(float(signals.publish_stats["success"]) * 1.5, 5.0)
    return _clamp_score(score)


def build_channel_health(
    channels: list[ChannelProfile],
    analytics_summary: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return enrich_channel_health(channels, analytics_summary)


def build_asset_ranking(perf_rows: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    ranked = [row for row in perf_rows if row.get("views") is not None]
    ranked.sort(key=lambda row: (row.get("ctr") or 0, row.get("views") or 0), reverse=True)
    ranking: list[dict[str, Any]] = []
    for row in ranked[:limit]:
        ranking.append(
            {
                "title": row.get("title") or row.get("topic"),
                "platform": row.get("platform"),
                "views": row.get("views"),
                "ctr": row.get("ctr"),
                "retention_pct": row.get("retention_pct"),
                "performance_tier": row.get("performance_tier"),
            }
        )
    return ranking


def build_opportunities(
    *,
    channels: list[ChannelProfile],
    competitors: list[CompetitorProfile],
    signals: GrowthReportSignals,
    performance: PerformanceInterpretation | None = None,
) -> list[str]:
    items: list[str] = list(performance.opportunities) if performance else []
    if items:
        pass
    else:
        for row in signals.perf_rows:
            if row.get("performance_tier") == "high":
                title = row.get("title") or row.get("topic")
                if title:
                    items.append(f"Replicar formato de alto desempenho: «{str(title)[:80]}»")
                    break
    for competitor in competitors:
        metrics = competitor.metrics or {}
        analysis = metrics.get("analysis") or {}
        if analysis.get("summary"):
            items.append(f"Benchmark: {analysis['summary'][:120]}")
            break
    if signals.content_rec_summary and "recomendação" in signals.content_rec_summary.lower():
        items.append(signals.content_rec_summary[:160])
    if channels and not any(ch.analyzed_at for ch in channels):
        items.append("Executar análise dos canais conectados para liberar insights de formato.")
    return items[:6]


def build_risks(
    *,
    channels: list[ChannelProfile],
    signals: GrowthReportSignals,
    performance: PerformanceInterpretation | None = None,
) -> list[str]:
    risks: list[str] = list(performance.risks) if performance else []
    disconnected = [ch.name for ch in channels if not ch.has_credentials]
    if disconnected:
        risks.append(f"Canais sem OAuth: {', '.join(disconnected[:3])}")
    if signals.publish_stats.get("failed"):
        risks.append(f"{signals.publish_stats['failed']} tentativa(s) de publicação falharam recentemente.")
    if signals.quality_stats.get("pass_rate") is not None and float(signals.quality_stats["pass_rate"]) < 0.7:
        risks.append("Taxa de aprovação de qualidade técnica abaixo de 70% nos pipelines recentes.")
    if not signals.analytics_summary.get("snapshot_count"):
        risks.append("Sem snapshots de analytics OAuth — decisões baseadas em dados limitados.")
    if signals.quality_stats.get("avg_score") is not None and float(signals.quality_stats["avg_score"]) < 6:
        risks.append(f"Score técnico médio baixo ({signals.quality_stats['avg_score']}/10).")
    return risks[:6]


def merge_recommendations(
    *,
    project_id: str,
    stored: list[GrowthRecommendation],
    content_recs: list[dict[str, Any]],
) -> list[GrowthRecommendation]:
    merged = list(stored)
    seen = {f"{rec.kind}:{rec.title}" for rec in merged}
    for item in content_recs:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        key = f"{item.get('kind', 'content')}:{title}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(
            GrowthRecommendation(
                id=None,
                project_id=project_id,
                channel_id=None,
                kind=str(item.get("kind") or "content"),
                title=title,
                detail=str(item.get("detail") or ""),
                priority=_CONFIDENCE_TO_PRIORITY.get(str(item.get("confidence") or "medium"), "medium"),
                source=str(item.get("source") or "content_recommendations"),
            )
        )
    return merged[:20]


def build_growth_strategy(
    *,
    project_id: str,
    base: GrowthStrategy | None,
    signals: GrowthReportSignals,
) -> GrowthStrategy:
    positioning = (
        signals.memory_mission
        or signals.memory_niche
        or (base.goals[0] if base and base.goals else "")
        or "Validar crescimento com canais conectados"
    )
    goals = list(base.goals) if base and base.goals else []
    if signals.memory_goal and signals.memory_goal not in goals:
        goals.insert(0, signals.memory_goal)
    if not goals:
        goals = ["Consolidar métricas OAuth e learning no relatório de crescimento"]

    kpis = dict(base.kpis) if base else {}
    kpis.update(
        {
            "platform_views": signals.analytics_summary.get("platforms"),
            "snapshot_count": signals.analytics_summary.get("snapshot_count"),
            "learning_samples": len(signals.learning_rows),
            "performance_samples": len(signals.perf_rows),
            "quality_pass_rate": signals.quality_stats.get("pass_rate"),
            "publish_success": signals.publish_stats.get("success"),
            "asset_count": signals.asset_count,
        }
    )

    cadence = dict(base.cadence) if base else {"weekly_posts": 3, "review_cycle": "weekly"}
    return GrowthStrategy(
        project_id=project_id,
        channel_id=base.channel_id if base else None,
        positioning=positioning,
        goals=goals,
        kpis=kpis,
        cadence=cadence,
        calendar=base.calendar if base else None,
        id=base.id if base else None,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


def assemble_growth_report(
    *,
    project_id: UUID,
    channels: list[ChannelProfile],
    competitors: list[CompetitorProfile],
    stored_recommendations: list[GrowthRecommendation],
    base_strategy: GrowthStrategy | None,
    signals: GrowthReportSignals,
) -> GrowthReport:
    pid = str(project_id)
    score = compute_growth_score(channels=channels, competitors=competitors, signals=signals)
    strategy = build_growth_strategy(project_id=pid, base=base_strategy, signals=signals)
    performance = interpret_performance_insights(pid, signals.perf_rows) if signals.perf_rows else None
    recommendations = merge_recommendations(
        project_id=pid,
        stored=stored_recommendations,
        content_recs=signals.content_recommendations,
    )
    if performance and performance.recommendations:
        perf_recs = [
            {
                "kind": rec.kind,
                "title": rec.title,
                "detail": rec.detail,
                "confidence": rec.priority,
                "source": rec.source,
            }
            for rec in performance.recommendations
        ]
        recommendations = merge_recommendations(project_id=pid, stored=recommendations, content_recs=perf_recs)
    channel_health = build_channel_health(channels, signals.analytics_summary)
    opportunities = build_opportunities(
        channels=channels, competitors=competitors, signals=signals, performance=performance
    )
    risks = build_risks(channels=channels, signals=signals, performance=performance)
    asset_ranking = performance.top_assets if performance and performance.top_assets else build_asset_ranking(signals.perf_rows)

    summary_parts = [
        f"{len(channels)} canal(is)",
        f"{len(competitors)} concorrente(s)",
        f"{len(recommendations)} recomendação(ões)",
    ]
    if signals.analytics_summary.get("snapshot_count"):
        summary_parts.append(f"{signals.analytics_summary['snapshot_count']} snapshots OAuth")
    if signals.perf_rows:
        summary_parts.append(f"{len(signals.perf_rows)} mídias em performance learning")
    summary = "Relatório consolidado — " + ", ".join(summary_parts) + "."

    return GrowthReport(
        project_id=pid,
        summary=summary,
        score=score,
        channels=channels,
        competitors=competitors,
        recommendations=recommendations,
        strategy=strategy,
        generated_at=datetime.now(timezone.utc).isoformat(),
        channel_health=channel_health,
        opportunities=opportunities,
        risks=risks,
        asset_ranking=asset_ranking,
        report_detail={
            "analytics_summary": signals.analytics_summary,
            "publish_stats": signals.publish_stats,
            "quality_stats": signals.quality_stats,
            "learning_samples": len(signals.learning_rows),
            "analytics_insights": len(signals.analytics_insights),
            "content_recommendations_summary": signals.content_rec_summary,
            "performance_learning": performance.to_dict() if performance else None,
        },
    )
