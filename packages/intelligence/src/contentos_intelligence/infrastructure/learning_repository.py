"""Persistence and KB sync indexing for Learning Engine — Epic 7."""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from contentos_intelligence.domain.learning import LearningReport


def _sync_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "")
    return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )


def _snippet(text: str, max_len: int = 400) -> str:
    t = (text or "").strip()
    return t if len(t) <= max_len else t[: max_len - 3] + "..."


class LearningRepository:
    async def save_report(self, db: AsyncSession, report: LearningReport) -> None:
        if not report.pipeline_id:
            return
        from contentos_database.models import LearningInsightRow

        pid = UUID(str(report.pipeline_id))
        project_id = UUID(str(report.project_id))
        existing = (
            await db.execute(select(LearningInsightRow).where(LearningInsightRow.pipeline_id == pid))
        ).scalar_one_or_none()
        payload = report.to_dict()
        if existing:
            existing.topic = report.topic
            existing.content_score = report.content_score
            existing.viral_score = report.viral_score
            existing.specialist_id = report.specialist_id
            existing.hook_text = report.hook_text
            existing.cta_text = report.cta_text
            existing.signals = payload.get("signals")
            existing.memory_applied = report.memory_applied
            existing.memory_updates = report.memory_updates
            existing.kb_indexed_count = report.kb_indexed_count
        else:
            db.add(
                LearningInsightRow(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    pipeline_id=pid,
                    topic=report.topic,
                    content_score=report.content_score,
                    viral_score=report.viral_score,
                    specialist_id=report.specialist_id,
                    hook_text=report.hook_text,
                    cta_text=report.cta_text,
                    signals=payload.get("signals"),
                    memory_applied=report.memory_applied,
                    memory_updates=report.memory_updates,
                    kb_indexed_count=report.kb_indexed_count,
                )
            )
        await db.flush()

    async def get_by_pipeline(self, db: AsyncSession, pipeline_id: UUID) -> dict[str, Any] | None:
        from contentos_database.models import LearningInsightRow

        row = (
            await db.execute(select(LearningInsightRow).where(LearningInsightRow.pipeline_id == pipeline_id))
        ).scalar_one_or_none()
        return _row_to_dict(row) if row else None

    async def list_by_project(
        self, db: AsyncSession, project_id: UUID, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        from contentos_database.models import LearningInsightRow

        rows = (
            await db.execute(
                select(LearningInsightRow)
                .where(LearningInsightRow.project_id == project_id)
                .order_by(desc(LearningInsightRow.created_at))
                .limit(limit)
            )
        ).scalars().all()
        return [_row_to_dict(r) for r in rows]

    def save_report_sync(self, report: LearningReport) -> None:
        sync_url = _sync_database_url()
        if not sync_url or not report.pipeline_id:
            return
        try:
            from contentos_database.models import LearningInsightRow
            from sqlalchemy import create_engine

            engine = create_engine(sync_url, pool_pre_ping=True)
            pid = UUID(str(report.pipeline_id))
            project_id = UUID(str(report.project_id))
            payload = report.to_dict()
            with Session(engine) as session:
                existing = session.execute(
                    select(LearningInsightRow).where(LearningInsightRow.pipeline_id == pid)
                ).scalar_one_or_none()
                if existing:
                    existing.topic = report.topic
                    existing.content_score = report.content_score
                    existing.viral_score = report.viral_score
                    existing.specialist_id = report.specialist_id
                    existing.hook_text = report.hook_text
                    existing.cta_text = report.cta_text
                    existing.signals = payload.get("signals")
                    existing.memory_applied = report.memory_applied
                    existing.memory_updates = report.memory_updates
                    existing.kb_indexed_count = report.kb_indexed_count
                else:
                    session.add(
                        LearningInsightRow(
                            id=uuid.uuid4(),
                            project_id=project_id,
                            pipeline_id=pid,
                            topic=report.topic,
                            content_score=report.content_score,
                            viral_score=report.viral_score,
                            specialist_id=report.specialist_id,
                            hook_text=report.hook_text,
                            cta_text=report.cta_text,
                            signals=payload.get("signals"),
                            memory_applied=report.memory_applied,
                            memory_updates=report.memory_updates,
                            kb_indexed_count=report.kb_indexed_count,
                        )
                    )
                session.commit()
        except Exception:
            pass


def index_learning_signals_sync(project_id: UUID, pipeline_id: UUID, report: LearningReport) -> int:
    """Insert learning-derived KB rows (text-only; embeddings optional later)."""
    sync_url = _sync_database_url()
    if not sync_url:
        return 0
    try:
        from contentos_database.models import KnowledgeEntry, Project
        from sqlalchemy import create_engine

        engine = create_engine(sync_url, pool_pre_ping=True)
        count = 0
        with Session(engine) as session:
            org_id = None
            project = session.get(Project, project_id)
            if project:
                org_id = project.org_id

            def _add(resource_type: str, title: str, content: str, metadata: dict | None = None) -> None:
                nonlocal count
                if not content.strip():
                    return
                session.add(
                    KnowledgeEntry(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        org_id=org_id,
                        pipeline_id=pipeline_id,
                        resource_type=resource_type,
                        resource_id=None,
                        title=title,
                        content_text=content,
                        snippet=_snippet(content),
                        metadata_=metadata,
                        version=1,
                    )
                )
                count += 1

            if report.hook_text:
                _add("hook", f"Learned hook: {report.topic}", report.hook_text, {"source": "learning"})
            if report.cta_text:
                _add("cta", f"Learned CTA: {report.topic}", report.cta_text, {"source": "learning"})
            if report.specialist_id:
                body = report.specialist_id
                for signal in report.signals:
                    if signal.signal_type == "specialist":
                        body = f"{signal.metadata.get('name', body)}\n{signal.metadata.get('context', '')}"
                        break
                _add("prompt", f"Specialist: {report.topic}", body, {"specialist_id": report.specialist_id})
            for signal in report.signals:
                if signal.signal_type != "prompt":
                    continue
                version = signal.metadata.get("version", "")
                content = f"{signal.value} v{version}".strip()
                _add(
                    "prompt",
                    f"Prompt {signal.value}",
                    content,
                    {"version": version, "source": "learning"},
                )
            session.commit()
        return count
    except Exception:
        return 0


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "pipeline_id": str(row.pipeline_id),
        "topic": row.topic,
        "content_score": row.content_score,
        "viral_score": row.viral_score,
        "specialist_id": row.specialist_id,
        "hook_text": row.hook_text,
        "cta_text": row.cta_text,
        "signals": row.signals or [],
        "memory_applied": row.memory_applied,
        "memory_updates": row.memory_updates or [],
        "kb_indexed_count": row.kb_indexed_count,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
