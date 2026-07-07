"""Next-video recommendation loop — phase 7.5."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import desc, select

from contentos_intelligence.application.performance_learning import list_performance_insights
from contentos_intelligence.domain.content_recommendation import (
    ContentRecommendation,
    ContentRecommendationReport,
)

try:
    from contentos_database.models import CommentAnalysisRow, LearningInsightRow, Project
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover
    AsyncSession = object  # type: ignore[misc, assignment]


async def build_project_recommendations(db: AsyncSession, project_id: UUID) -> ContentRecommendationReport:
    recs: list[ContentRecommendation] = []
    seen: set[str] = set()

    def add(rec: ContentRecommendation) -> None:
        key = f"{rec.kind}:{rec.title}"
        if key in seen:
            return
        seen.add(key)
        recs.append(rec)

    perf_rows = await list_performance_insights(db, project_id, limit=30)
    high = [r for r in perf_rows if r.get("performance_tier") == "high"]
    high.sort(key=lambda r: (r.get("ctr") or 0, r.get("views") or 0), reverse=True)

    for row in high[:5]:
        platform = row.get("platform") or "platform"
        hook = row.get("topic") or row.get("title")
        learnings = row.get("learnings") or []
        for line in learnings:
            if "hook" in str(line).lower() and not hook:
                hook = str(line)
                break
        if hook:
            add(
                ContentRecommendation(
                    kind="hook",
                    title=f"Repetir hook em {platform}",
                    detail=f"CTR {row.get('ctr') or 0:.1%} · {row.get('views', 0)} views — «{str(hook)[:120]}»",
                    confidence="high",
                    source="performance_learning",
                    action_href="/factory",
                )
            )
        if row.get("retention_delta") is not None and float(row["retention_delta"]) >= 5:
            add(
                ContentRecommendation(
                    kind="retention",
                    title="Manter estrutura de retenção",
                    detail=f"Retenção real superou previsão em {float(row['retention_delta']):.1f} p.p. no tópico «{row.get('topic', '')[:80]}»",
                    confidence="high",
                    source="performance_learning",
                )
            )

    learning_rows = await _load_learning_rows(db, project_id)
    for row in learning_rows[:5]:
        topic = (row.topic or "").strip()
        if topic:
            add(
                ContentRecommendation(
                    kind="topic",
                    title=f"Novo vídeo: {topic[:80]}",
                    detail=f"Learning score viral {row.viral_score or '—'} · hook conhecido no projeto",
                    confidence="medium",
                    source="learning",
                    action_href="/factory",
                )
            )
        if row.hook_text:
            add(
                ContentRecommendation(
                    kind="hook",
                    title="Hook com histórico no projeto",
                    detail=row.hook_text[:200],
                    confidence="medium",
                    source="learning",
                )
            )

    comment_rows = await _load_comment_insights(db, project_id)
    for row in comment_rows[:3]:
        themes = row.themes if isinstance(row.themes, list) else []
        theme = str(themes[0]) if themes else (row.title or "")
        theme = theme.strip()
        if theme:
            add(
                ContentRecommendation(
                    kind="audience",
                    title="Ângulo sugerido pela audiência",
                    detail=theme[:220],
                    confidence="medium",
                    source="comment_analyzer",
                    action_href="/community",
                )
            )

    project = await db.get(Project, project_id)
    if project:
        niche = (project.description or project.name or "").strip()
        if niche and len(recs) < 3:
            add(
                ContentRecommendation(
                    kind="topic",
                    title=f"Explorar nicho: {niche[:60]}",
                    detail="Sem snapshots OAuth suficientes — use o DNA do projeto como ponto de partida.",
                    confidence="low",
                    source="project",
                    action_href="/factory",
                )
            )

    if not perf_rows:
        summary = "Conecte OAuth e execute sync em /analytics para recomendações baseadas em performance."
    elif not recs:
        summary = f"{len(perf_rows)} mídias analisadas — ainda sem padrão forte para o próximo vídeo."
    else:
        summary = f"{len(recs)} recomendação(ões) a partir de performance, learning e comentários."

    return ContentRecommendationReport(
        project_id=str(project_id),
        recommendations=recs[:12],
        summary=summary,
    )


async def _load_learning_rows(db: AsyncSession, project_id: UUID) -> list[Any]:
    result = await db.execute(
        select(LearningInsightRow)
        .where(LearningInsightRow.project_id == project_id)
        .order_by(desc(LearningInsightRow.created_at))
        .limit(20)
    )
    return list(result.scalars().all())


async def _load_comment_insights(db: AsyncSession, project_id: UUID) -> list[Any]:
    result = await db.execute(
        select(CommentAnalysisRow)
        .where(CommentAnalysisRow.project_id == project_id)
        .order_by(desc(CommentAnalysisRow.created_at))
        .limit(10)
    )
    return list(result.scalars().all())
