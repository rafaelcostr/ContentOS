"""Creative Memory agent — merge KB + Learning (V5.2.5)."""

from __future__ import annotations

import json
import os

from contentos_intelligence.application.creative_memory import (
    creative_memory_enabled,
    merge_creative_memory,
    merge_creative_memory_async,
)
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

try:
    from contentos_events import DomainEvent, get_event_bus
    from contentos_events.domain.event_types import CREATIVE_MEMORY_MERGED
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]
    CREATIVE_MEMORY_MERGED = "creative_memory.merged"  # type: ignore[misc]

    def get_event_bus():  # type: ignore[misc]
        return None


def _async_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return ""
    return database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )


class CreativeMemoryAgentHandler(BaseAgentHandler):
    step = "creative_memory"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        if not creative_memory_enabled():
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                data={"creative_memory_skipped": True},
                logs=["[creative_memory] Disabled via CREATIVE_MEMORY_ENABLED"],
            )

        topic = str(task_input.payload.get("topic") or "")
        logs = [f"[creative_memory] Merging KB + Learning for pipeline {task_input.pipeline_id}"]
        context = IntelligenceContext(
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            topic=topic,
            payload=dict(task_input.payload),
        )

        database_url = _async_database_url()
        if database_url:
            engine = None
            try:
                engine = create_async_engine(database_url, pool_pre_ping=True)
                session_factory = async_sessionmaker(engine, expire_on_commit=False)
                async with session_factory() as db:
                    report = await merge_creative_memory_async(context, db)
                    await db.commit()
            except Exception as exc:
                logs.append(f"Async KB merge fallback: {exc}")
                report = merge_creative_memory(context)
            finally:
                if engine is not None:
                    await engine.dispose()
        else:
            logs.append("DATABASE_URL not configured; sync merge only")
            report = merge_creative_memory(context)

        report_dict = report.to_dict()
        logs.append(
            f"Memory applied={report.memory_applied} KB hits={len(report.knowledge_hits)} "
            f"indexed={report.knowledge_indexed_count}"
        )

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(report_dict, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="creative_memory.json",
                content_type="application/json",
            ),
        )
        self._publish_event(task_input, report_dict)

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "creative_memory": report_dict,
                "creative_memory_report": report_dict,
                "creative_memory_context": report.creative_memory_context,
                "creative_memory_hints": report.hints,
                "memory_applied": report.memory_applied,
                "kb_indexed_count": report.kb_indexed_count,
                "knowledge_indexed_count": report.knowledge_indexed_count,
            },
            logs=logs,
        )

    def _publish_event(self, task_input: AgentTaskInput, report: dict) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent:
                return
            event = DomainEvent(
                event_type=CREATIVE_MEMORY_MERGED,
                pipeline_id=task_input.pipeline_id,
                project_id=task_input.project_id,
                job_id=task_input.job_id,
                agent="creative_memory",
                step=self.step,
                status="completed",
                payload=report,
            )
            bus.publish_sync(event)
        except Exception:
            pass
