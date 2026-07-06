"""PostgreSQL repository for analytics insights."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from contentos_analytics_ai.domain.insight import AnalyticsInsightData
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class InsightRepository:
    async def save(self, db: AsyncSession, data: AnalyticsInsightData) -> dict[str, Any]:
        from contentos_database.models import AnalyticsInsight

        result = await db.execute(
            select(AnalyticsInsight).where(AnalyticsInsight.pipeline_id == data.pipeline_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.metrics = data.metrics
            row.analysis = data.analysis
            row.models_used = data.models_used
            row.prompts_used = data.prompts_used
            row.applied_to_memory = data.applied_to_memory
            row.video_id = data.video_id
        else:
            row = AnalyticsInsight(
                id=uuid.uuid4(),
                project_id=data.project_id,
                pipeline_id=data.pipeline_id,
                video_id=data.video_id,
                metrics=data.metrics,
                analysis=data.analysis,
                models_used=data.models_used,
                prompts_used=data.prompts_used,
                applied_to_memory=data.applied_to_memory,
            )
            db.add(row)
        await db.flush()
        return _row_to_dict(row)

    async def get_by_pipeline(self, db: AsyncSession, pipeline_id: UUID) -> dict | None:
        from contentos_database.models import AnalyticsInsight

        result = await db.execute(select(AnalyticsInsight).where(AnalyticsInsight.pipeline_id == pipeline_id))
        row = result.scalar_one_or_none()
        return _row_to_dict(row) if row else None

    async def list_recent(self, db: AsyncSession, limit: int = 50) -> list[dict]:
        from contentos_database.models import AnalyticsInsight

        result = await db.execute(
            select(AnalyticsInsight).order_by(AnalyticsInsight.created_at.desc()).limit(limit)
        )
        return [_row_to_dict(r) for r in result.scalars().all()]

    async def list_by_project(self, db: AsyncSession, project_id: UUID, limit: int = 10) -> list[dict]:
        from contentos_database.models import AnalyticsInsight

        result = await db.execute(
            select(AnalyticsInsight)
            .where(AnalyticsInsight.project_id == project_id)
            .order_by(AnalyticsInsight.created_at.desc())
            .limit(limit)
        )
        return [_row_to_dict(r) for r in result.scalars().all()]


def save_sync(data: AnalyticsInsightData) -> bool:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return False
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import AnalyticsInsight
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            row = session.execute(
                select(AnalyticsInsight).where(AnalyticsInsight.pipeline_id == data.pipeline_id)
            ).scalar_one_or_none()
            if row:
                row.metrics = data.metrics
                row.analysis = data.analysis
                row.models_used = data.models_used
                row.prompts_used = data.prompts_used
                row.applied_to_memory = data.applied_to_memory
                row.video_id = data.video_id
            else:
                row = AnalyticsInsight(
                    id=uuid.uuid4(),
                    project_id=data.project_id,
                    pipeline_id=data.pipeline_id,
                    video_id=data.video_id,
                    metrics=data.metrics,
                    analysis=data.analysis,
                    models_used=data.models_used,
                    prompts_used=data.prompts_used,
                    applied_to_memory=data.applied_to_memory,
                    created_at=datetime.now(UTC),
                )
                session.add(row)
            session.commit()
        return True
    except Exception:
        return False


def list_by_project_sync(project_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
    """Load recent analytics insights for a project (sync — agent workers)."""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return []
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import AnalyticsInsight
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            rows = session.execute(
                select(AnalyticsInsight)
                .where(AnalyticsInsight.project_id == project_id)
                .order_by(AnalyticsInsight.created_at.desc())
                .limit(limit)
            ).scalars().all()
            return [_row_to_dict(r) for r in rows]
    except Exception:
        return []


def _row_to_dict(row) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "pipeline_id": str(row.pipeline_id),
        "video_id": str(row.video_id) if row.video_id else None,
        "metrics": row.metrics or {},
        "analysis": row.analysis or {},
        "models_used": row.models_used or {},
        "prompts_used": row.prompts_used or {},
        "applied_to_memory": row.applied_to_memory,
        "score": (row.analysis or {}).get("score"),
        "summary": (row.analysis or {}).get("summary"),
        "created_at": row.created_at.isoformat(),
    }
