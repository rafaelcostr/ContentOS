"""Index pipeline artifacts into the Knowledge Base."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.application.knowledge_base import KnowledgeBaseService
from contentos_intelligence.domain.knowledge_entry import KnowledgeEntryData


def _snippet(text: str, max_len: int = 400) -> str:
    t = (text or "").strip()
    return t if len(t) <= max_len else t[: max_len - 3] + "..."


class KnowledgeIndexer:
    """Extracts scripts, hooks, videos, analytics from a completed pipeline."""

    def __init__(self, kb: KnowledgeBaseService) -> None:
        self._kb = kb

    async def index_pipeline(self, db: AsyncSession, pipeline_id: UUID) -> list[KnowledgeEntryData]:
        from contentos_database.models import AnalyticsInsight, Pipeline, Script, Video

        pipeline = await db.get(Pipeline, pipeline_id)
        if not pipeline:
            return []

        project_id = pipeline.project_id
        org_id = None
        from contentos_database.models import Project

        project = await db.get(Project, project_id)
        if project:
            org_id = project.org_id

        indexed: list[KnowledgeEntryData] = []

        scripts = (
            await db.execute(select(Script).where(Script.pipeline_id == pipeline_id))
        ).scalars().all()
        for script in scripts:
            indexed.append(
                await self._kb.index_entry(
                    KnowledgeEntryData(
                        id=None,
                        project_id=project_id,
                        org_id=org_id,
                        pipeline_id=pipeline_id,
                        resource_type="script",
                        resource_id=script.id,
                        title=script.title or "Script",
                        content_text=script.full_text or "",
                        snippet=_snippet(script.full_text or ""),
                        metadata={"hook": script.hook, "cta": script.call_to_action},
                    )
                )
            )
            if script.hook:
                indexed.append(
                    await self._kb.index_entry(
                        KnowledgeEntryData(
                            id=None,
                            project_id=project_id,
                            org_id=org_id,
                            pipeline_id=pipeline_id,
                            resource_type="hook",
                            resource_id=script.id,
                            title=f"Hook: {script.title or pipeline_id}",
                            content_text=script.hook,
                            snippet=_snippet(script.hook, 200),
                            metadata={"script_id": str(script.id)},
                        )
                    )
                )
            if script.call_to_action:
                indexed.append(
                    await self._kb.index_entry(
                        KnowledgeEntryData(
                            id=None,
                            project_id=project_id,
                            org_id=org_id,
                            pipeline_id=pipeline_id,
                            resource_type="cta",
                            resource_id=script.id,
                            title=f"CTA: {script.title or pipeline_id}",
                            content_text=script.call_to_action,
                            snippet=_snippet(script.call_to_action, 200),
                        )
                    )
                )

        videos = (
            await db.execute(select(Video).where(Video.pipeline_id == pipeline_id))
        ).scalars().all()
        for video in videos:
            body = f"{video.title}\n{video.description or ''}"
            indexed.append(
                await self._kb.index_entry(
                    KnowledgeEntryData(
                        id=None,
                        project_id=project_id,
                        org_id=org_id,
                        pipeline_id=pipeline_id,
                        resource_type="video",
                        resource_id=video.id,
                        title=video.title,
                        content_text=body,
                        snippet=_snippet(body),
                        metadata={"hashtags": video.hashtags or []},
                    )
                )
            )
            indexed.append(
                await self._kb.index_entry(
                    KnowledgeEntryData(
                        id=None,
                        project_id=project_id,
                        org_id=org_id,
                        pipeline_id=pipeline_id,
                        resource_type="title",
                        resource_id=video.id,
                        title=video.title,
                        content_text=video.title,
                        snippet=video.title[:200],
                    )
                )
            )

        insight = (
            await db.execute(
                select(AnalyticsInsight).where(AnalyticsInsight.pipeline_id == pipeline_id)
            )
        ).scalar_one_or_none()
        if insight:
            summary = (insight.analysis or {}).get("summary", "")
            indexed.append(
                await self._kb.index_entry(
                    KnowledgeEntryData(
                        id=None,
                        project_id=project_id,
                        org_id=org_id,
                        pipeline_id=pipeline_id,
                        resource_type="analytics",
                        resource_id=insight.id,
                        title="Analytics insight",
                        content_text=summary or str(insight.analysis or {}),
                        snippet=_snippet(summary or ""),
                        metadata={"metrics": insight.metrics or {}},
                    )
                )
            )

        return indexed
