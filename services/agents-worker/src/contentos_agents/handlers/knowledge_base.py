"""Knowledge Base step — indexes pipeline artifacts into permanent memory."""

from __future__ import annotations

import json
import os

from contentos_intelligence.application.knowledge_base import KnowledgeBaseService
from contentos_intelligence.application.knowledge_indexer import KnowledgeIndexer
from contentos_intelligence.infrastructure.embedding_client import get_gateway_embedding_client
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

try:
    from contentos_events import DomainEvent, get_event_bus
    from contentos_events.domain.event_types import KNOWLEDGE_BASE_INDEXED
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]
    KNOWLEDGE_BASE_INDEXED = "knowledge_base.indexed"  # type: ignore[misc]

    def get_event_bus():  # type: ignore[misc]
        return None


def _async_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return ""
    return database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )


class KnowledgeBaseAgentHandler(BaseAgentHandler):
    step = "knowledge_base"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        logs = [f"[knowledge_base] Indexing pipeline {task_input.pipeline_id}"]
        database_url = _async_database_url()
        if not database_url:
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                data={"knowledge_base_skipped": True, "knowledge_base_reason": "DATABASE_URL not configured"},
                logs=logs + ["DATABASE_URL not configured; skipped"],
            )

        report = {
            "knowledge_base_indexed": False,
            "knowledge_indexed_count": 0,
            "knowledge_entries": [],
            "content_graph_built": False,
        }
        engine = create_async_engine(database_url, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with session_factory() as db:
                kb = KnowledgeBaseService(db, get_gateway_embedding_client())
                indexed = await KnowledgeIndexer(kb).index_pipeline(db, task_input.pipeline_id)
                report["knowledge_base_indexed"] = True
                report["knowledge_indexed_count"] = len(indexed)
                report["knowledge_entries"] = [
                    {
                        "id": str(entry.id) if entry.id else None,
                        "resource_type": entry.resource_type,
                        "resource_id": str(entry.resource_id) if entry.resource_id else None,
                        "title": entry.title,
                        "has_embedding": bool(entry.embedding),
                    }
                    for entry in indexed
                ]

                try:
                    from contentos_intelligence.application.content_graph import (
                        ContentGraphService,
                        is_content_graph_enabled,
                    )

                    if is_content_graph_enabled():
                        await ContentGraphService().build_pipeline(db, task_input.pipeline_id)
                        report["content_graph_built"] = True
                except Exception as exc:
                    logs.append(f"Content graph skipped: {exc}")

                await db.commit()
        except Exception as exc:
            logs.append(f"Knowledge indexing unavailable: {exc}")
            report["knowledge_base_indexed"] = False
            report["knowledge_base_error"] = str(exc)
        finally:
            await engine.dispose()

        logs.append(f"Knowledge entries indexed: {report['knowledge_indexed_count']}")
        if report.get("content_graph_built"):
            logs.append("Content graph updated")

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(report, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="knowledge_base_report.json",
                content_type="application/json",
            ),
        )
        self._publish_knowledge_event(task_input, report)

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "knowledge_base_report": report,
                "knowledge_indexed_count": report["knowledge_indexed_count"],
                "content_graph_built": report["content_graph_built"],
            },
            logs=logs,
        )

    def _publish_knowledge_event(self, task_input: AgentTaskInput, report: dict) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent:
                return
            event = DomainEvent(
                event_type=KNOWLEDGE_BASE_INDEXED,
                pipeline_id=task_input.pipeline_id,
                project_id=task_input.project_id,
                job_id=task_input.job_id,
                agent="knowledge_base",
                step=self.step,
                status="completed",
                payload=report,
            )
            bus.publish_sync(event)
        except Exception:
            pass
