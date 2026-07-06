"""Persistence for trend forecasts — Epic 10."""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from contentos_intelligence.domain.trend_forecast import TrendForecastReport


def _sync_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "")
    return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )


class TrendForecastRepository:
    async def save_report(self, db: AsyncSession, report: TrendForecastReport) -> None:
        if not report.pipeline_id:
            return
        from contentos_database.models import TrendForecastRow

        pid = UUID(str(report.pipeline_id))
        project_id = UUID(str(report.project_id))
        existing = (
            await db.execute(select(TrendForecastRow).where(TrendForecastRow.pipeline_id == pid))
        ).scalar_one_or_none()
        if existing:
            existing.topic = report.topic
            existing.niche = report.niche
            existing.trend_score = report.trend_score
            existing.expected_growth = report.expected_growth
            existing.production_recommendation = report.production_recommendation
            existing.report = report.to_dict()
        else:
            db.add(
                TrendForecastRow(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    pipeline_id=pid,
                    topic=report.topic,
                    niche=report.niche,
                    trend_score=report.trend_score,
                    expected_growth=report.expected_growth,
                    production_recommendation=report.production_recommendation,
                    report=report.to_dict(),
                )
            )
        await db.flush()

    async def get_by_pipeline(self, db: AsyncSession, pipeline_id: UUID) -> dict[str, Any] | None:
        from contentos_database.models import TrendForecastRow

        row = (
            await db.execute(select(TrendForecastRow).where(TrendForecastRow.pipeline_id == pipeline_id))
        ).scalar_one_or_none()
        return _row_to_dict(row) if row else None

    def save_report_sync(self, report: TrendForecastReport) -> None:
        sync_url = _sync_database_url()
        if not sync_url or not report.pipeline_id:
            return
        try:
            from contentos_database.models import TrendForecastRow
            from sqlalchemy import create_engine

            engine = create_engine(sync_url, pool_pre_ping=True)
            pid = UUID(str(report.pipeline_id))
            project_id = UUID(str(report.project_id))
            payload = report.to_dict()
            with Session(engine) as session:
                existing = session.execute(
                    select(TrendForecastRow).where(TrendForecastRow.pipeline_id == pid)
                ).scalar_one_or_none()
                if existing:
                    existing.topic = report.topic
                    existing.niche = report.niche
                    existing.trend_score = report.trend_score
                    existing.expected_growth = report.expected_growth
                    existing.production_recommendation = report.production_recommendation
                    existing.report = payload
                else:
                    session.add(
                        TrendForecastRow(
                            id=uuid.uuid4(),
                            project_id=project_id,
                            pipeline_id=pid,
                            topic=report.topic,
                            niche=report.niche,
                            trend_score=report.trend_score,
                            expected_growth=report.expected_growth,
                            production_recommendation=report.production_recommendation,
                            report=payload,
                        )
                    )
                session.commit()
        except Exception:
            pass


def count_kb_entries_sync(project_id: UUID) -> int:
    sync_url = _sync_database_url()
    if not sync_url:
        return 0
    try:
        from contentos_database.models import KnowledgeEntry
        from sqlalchemy import create_engine

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            return int(
                session.execute(
                    select(func.count()).select_from(KnowledgeEntry).where(KnowledgeEntry.project_id == project_id)
                ).scalar_one()
                or 0
            )
    except Exception:
        return 0


def list_learning_insights_sync(project_id: UUID, *, limit: int = 10) -> list[dict[str, Any]]:
    sync_url = _sync_database_url()
    if not sync_url:
        return []
    try:
        from contentos_database.models import LearningInsightRow
        from sqlalchemy import create_engine

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            rows = (
                session.execute(
                    select(LearningInsightRow)
                    .where(LearningInsightRow.project_id == project_id)
                    .order_by(desc(LearningInsightRow.created_at))
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [
                {
                    "content_score": r.content_score,
                    "viral_score": r.viral_score,
                    "topic": r.topic,
                }
                for r in rows
            ]
    except Exception:
        return []


def _row_to_dict(row: Any) -> dict[str, Any]:
    report = row.report or {}
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "pipeline_id": str(row.pipeline_id),
        "topic": row.topic,
        "niche": row.niche,
        "trend_score": row.trend_score,
        "expected_growth": row.expected_growth,
        "production_recommendation": row.production_recommendation,
        **report,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
