"""ExecutiveSummaryService — aggregate V4 module metrics (Epic 12)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.domain.executive_summary import ExecutiveSummary, ModuleStatus


def _module_status(key: str, label: str, metric: str, href: str, *, detail: str = "", active: bool = True) -> ModuleStatus:
    return ModuleStatus(
        key=key,
        label=label,
        status="active" if active else "empty",
        metric=metric,
        href=href,
        detail=detail,
    )


class ExecutiveSummaryService:
    async def build(self, db: AsyncSession, project_id: UUID, *, project_name: str = "") -> ExecutiveSummary:
        from contentos_database.models import (
            AbVariantRow,
            ContentRelationRow,
            KnowledgeEntry,
            LearningInsightRow,
            Pipeline,
            PipelineStatus,
            Project,
            TrendForecastRow,
        )

        from contentos_intelligence.application.specialists.catalog import list_specialists

        project = await db.get(Project, project_id)
        name = project_name or (project.name if project else "")

        pipelines_total = (
            await db.execute(select(func.count()).select_from(Pipeline).where(Pipeline.project_id == project_id))
        ).scalar_one() or 0
        pipelines_completed = (
            await db.execute(
                select(func.count())
                .select_from(Pipeline)
                .where(Pipeline.project_id == project_id, Pipeline.status == PipelineStatus.COMPLETED)
            )
        ).scalar_one() or 0

        knowledge_entries = (
            await db.execute(
                select(func.count()).select_from(KnowledgeEntry).where(KnowledgeEntry.project_id == project_id)
            )
        ).scalar_one() or 0

        learning_rows = (
            await db.execute(
                select(LearningInsightRow)
                .where(LearningInsightRow.project_id == project_id)
                .order_by(desc(LearningInsightRow.created_at))
                .limit(20)
            )
        ).scalars().all()
        learning_insights = len(learning_rows)

        graph_edges = (
            await db.execute(
                select(func.count()).select_from(ContentRelationRow).where(ContentRelationRow.project_id == project_id)
            )
        ).scalar_one() or 0

        graph_nodes: set[str] = set()
        rel_rows = (
            await db.execute(
                select(ContentRelationRow).where(ContentRelationRow.project_id == project_id).limit(1000)
            )
        ).scalars().all()
        for row in rel_rows:
            graph_nodes.add(f"{row.source_type}:{row.source_id}")
            graph_nodes.add(f"{row.target_type}:{row.target_id}")

        ab_variant_sets = (
            await db.execute(
                select(func.count(func.distinct(AbVariantRow.pipeline_id))).where(
                    AbVariantRow.project_id == project_id
                )
            )
        ).scalar_one() or 0

        latest_trend = (
            await db.execute(
                select(TrendForecastRow)
                .where(TrendForecastRow.project_id == project_id)
                .order_by(desc(TrendForecastRow.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()

        dna_preview = ""
        hook_patterns: list[str] = []
        try:
            from contentos_memory import get_memory_service

            memory = await get_memory_service().get_async(db, project_id)
            dna_preview = memory.format_dna_context()
            hook_patterns = list(memory.hook_patterns or [])[:6]
        except Exception:
            pass

        content_scores = [r.content_score for r in learning_rows if r.content_score is not None]
        viral_scores = [r.viral_score for r in learning_rows if r.viral_score is not None]
        avg_content = sum(content_scores) / len(content_scores) if content_scores else None
        avg_viral = sum(viral_scores) / len(viral_scores) if viral_scores else None
        latest_learning_topic = learning_rows[0].topic if learning_rows else None

        specialists = list_specialists(include_upcoming=False)

        modules = [
            _module_status(
                "viral",
                "Viral Intelligence",
                f"{avg_viral:.0f}" if avg_viral is not None else "—",
                "/viral",
                detail="Score médio (learning)",
                active=avg_viral is not None,
            ),
            _module_status(
                "knowledge",
                "Knowledge Base",
                str(knowledge_entries),
                "/knowledge",
                detail="entradas indexadas",
                active=knowledge_entries > 0,
            ),
            _module_status(
                "dna",
                "Project DNA",
                str(len(hook_patterns)),
                "/memory",
                detail="padrões de hook",
                active=bool(dna_preview or hook_patterns),
            ),
            _module_status(
                "content_score",
                "Content Score",
                f"{avg_content:.0f}" if avg_content is not None else "—",
                "/content-score",
                detail="média pipelines",
                active=avg_content is not None,
            ),
            _module_status(
                "ab_testing",
                "A/B Testing",
                str(ab_variant_sets),
                "/ab-testing",
                detail="pipelines com variantes",
                active=ab_variant_sets > 0,
            ),
            _module_status(
                "trend",
                "Trend Forecast",
                f"{latest_trend.trend_score:.0f}" if latest_trend else "—",
                "/trend-forecast",
                detail=latest_trend.expected_growth if latest_trend else "",
                active=latest_trend is not None,
            ),
            _module_status(
                "specialists",
                "Specialists",
                str(len(specialists)),
                "/specialists",
                detail="perfis ativos",
                active=len(specialists) > 0,
            ),
            _module_status(
                "learning",
                "Learning Engine",
                str(learning_insights),
                "/learning",
                detail=latest_learning_topic or "",
                active=learning_insights > 0,
            ),
            _module_status(
                "reuse",
                "Smart Reuse",
                "KB",
                "/knowledge",
                detail="busca + sugestões",
                active=knowledge_entries > 0,
            ),
            _module_status(
                "graph",
                "Content Graph",
                f"{len(graph_nodes)}",
                "/content-graph",
                detail=f"{graph_edges} arestas",
                active=graph_edges > 0,
            ),
            _module_status(
                "multi_content",
                "Multi Content",
                str(pipelines_completed),
                "/multi-content",
                detail="pipelines completos",
                active=pipelines_completed > 0,
            ),
        ]

        return ExecutiveSummary(
            project_id=str(project_id),
            project_name=name,
            pipelines_total=int(pipelines_total),
            pipelines_completed=int(pipelines_completed),
            knowledge_entries=int(knowledge_entries),
            learning_insights=learning_insights,
            graph_nodes=len(graph_nodes),
            graph_edges=int(graph_edges),
            ab_variant_sets=int(ab_variant_sets),
            specialists_available=len(specialists),
            avg_content_score=round(avg_content, 1) if avg_content is not None else None,
            avg_viral_score=round(avg_viral, 1) if avg_viral is not None else None,
            latest_trend_score=latest_trend.trend_score if latest_trend else None,
            latest_trend_growth=latest_trend.expected_growth if latest_trend else None,
            dna_preview=dna_preview,
            hook_patterns=hook_patterns,
            latest_learning_topic=latest_learning_topic,
            modules=modules,
        )
