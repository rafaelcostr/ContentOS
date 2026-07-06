"""Persistence for video platform variants — Epic 2b."""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from contentos_intelligence.domain.video_variants import VideoVariantsReport


class VideoVariantsRepository:
    async def save_report(self, db: AsyncSession, report: VideoVariantsReport) -> None:
        if not report.pipeline_id:
            return
        from contentos_database.models import VideoPlatformVariantRow

        pid = UUID(str(report.pipeline_id))
        await db.execute(delete(VideoPlatformVariantRow).where(VideoPlatformVariantRow.pipeline_id == pid))
        for variant in report.variants:
            row = VideoPlatformVariantRow(
                id=uuid.uuid4(),
                project_id=UUID(str(report.project_id)),
                pipeline_id=pid,
                platform=variant.platform,
                title=variant.title,
                description=variant.description,
                hashtags=variant.hashtags,
                crop_spec=variant.crop_spec.to_dict(),
                render_ref=variant.render_ref,
                metadata_=variant.metadata,
                source=variant.source,
            )
            db.add(row)
        await db.flush()

    async def list_by_pipeline(self, db: AsyncSession, pipeline_id: UUID) -> list[dict[str, Any]]:
        from contentos_database.models import VideoPlatformVariantRow

        rows = (
            await db.execute(
                select(VideoPlatformVariantRow)
                .where(VideoPlatformVariantRow.pipeline_id == pipeline_id)
                .order_by(VideoPlatformVariantRow.platform)
            )
        ).scalars().all()
        return [_row_to_dict(r) for r in rows]

    def save_report_sync(self, report: VideoVariantsReport) -> None:
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url or not report.pipeline_id:
            return
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
            "postgresql://", "postgresql+psycopg2://"
        )
        try:
            from contentos_database.models import VideoPlatformVariantRow
            from sqlalchemy import create_engine

            engine = create_engine(sync_url, pool_pre_ping=True)
            pid = UUID(str(report.pipeline_id))
            with Session(engine) as session:
                session.execute(
                    delete(VideoPlatformVariantRow).where(VideoPlatformVariantRow.pipeline_id == pid)
                )
                for variant in report.variants:
                    session.add(
                        VideoPlatformVariantRow(
                            id=uuid.uuid4(),
                            project_id=UUID(str(report.project_id)),
                            pipeline_id=pid,
                            platform=variant.platform,
                            title=variant.title,
                            description=variant.description,
                            hashtags=variant.hashtags,
                            crop_spec=variant.crop_spec.to_dict(),
                            render_ref=variant.render_ref,
                            metadata_=variant.metadata,
                            source=variant.source,
                        )
                    )
                session.commit()
        except Exception:
            pass


def update_video_platform_variants_sync(pipeline_id: UUID, variants_by_platform: dict[str, Any]) -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import Video
        from sqlalchemy import create_engine, select

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            row = session.execute(select(Video).where(Video.pipeline_id == pipeline_id)).scalar_one_or_none()
            if row:
                row.platform_variants = variants_by_platform
                session.commit()
    except Exception:
        pass


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "pipeline_id": str(row.pipeline_id),
        "platform": row.platform,
        "title": row.title,
        "description": row.description,
        "hashtags": row.hashtags or [],
        "crop_spec": row.crop_spec or {},
        "render_ref": row.render_ref,
        "data": row.metadata_ or {},
        "source": row.source,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
