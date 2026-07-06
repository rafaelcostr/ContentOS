"""Persist clip research + asset collector results per pipeline."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import UUID


class CollectionStore:
    def save_candidates(self, pipeline_id: UUID, project_id: UUID, candidates: list[dict]) -> bool:
        return _upsert(pipeline_id, project_id, candidates=candidates, status="researched")

    def save_assets(self, pipeline_id: UUID, project_id: UUID, assets: list[dict]) -> bool:
        return _upsert(pipeline_id, project_id, assets=assets, status="collected")

    def get_sync(self, pipeline_id: UUID) -> dict[str, Any] | None:
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            return None
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
            "postgresql://", "postgresql+psycopg2://"
        )
        try:
            from contentos_database.models import PipelineAssetCollection
            from sqlalchemy import create_engine, select
            from sqlalchemy.orm import Session

            engine = create_engine(sync_url, pool_pre_ping=True)
            with Session(engine) as session:
                row = session.execute(
                    select(PipelineAssetCollection).where(PipelineAssetCollection.pipeline_id == pipeline_id)
                ).scalar_one_or_none()
                if not row:
                    return None
                return {
                    "pipeline_id": str(row.pipeline_id),
                    "project_id": str(row.project_id),
                    "candidates": row.candidates or [],
                    "assets": row.assets or [],
                    "status": row.status,
                }
        except Exception:
            return None


def _upsert(
    pipeline_id: UUID,
    project_id: UUID,
    *,
    candidates: list[dict] | None = None,
    assets: list[dict] | None = None,
    status: str,
) -> bool:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return False
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import PipelineAssetCollection
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            row = session.execute(
                select(PipelineAssetCollection).where(PipelineAssetCollection.pipeline_id == pipeline_id)
            ).scalar_one_or_none()
            now = datetime.now(UTC)
            if row:
                if candidates is not None:
                    row.candidates = candidates
                if assets is not None:
                    row.assets = assets
                row.status = status
                row.updated_at = now
            else:
                row = PipelineAssetCollection(
                    id=uuid.uuid4(),
                    pipeline_id=pipeline_id,
                    project_id=project_id,
                    candidates=candidates or [],
                    assets=assets or [],
                    status=status,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            session.commit()
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def get_collection_store() -> CollectionStore:
    return CollectionStore()
