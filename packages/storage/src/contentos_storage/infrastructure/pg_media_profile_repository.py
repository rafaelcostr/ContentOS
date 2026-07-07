"""Persist asset media profiles (V5.0.3)."""

from __future__ import annotations

from uuid import UUID

from contentos_database.models import AssetMediaProfile
from contentos_storage.infrastructure.pg_asset_repository import _sync_url
from sqlalchemy import select
from sqlalchemy.orm import Session


class PgAssetMediaProfileRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url

    def _engine(self):
        from sqlalchemy import create_engine

        return create_engine(_sync_url(self._database_url), pool_pre_ping=True)

    def get_by_asset_id(self, asset_id: UUID) -> AssetMediaProfile | None:
        with Session(self._engine()) as session:
            return session.scalar(
                select(AssetMediaProfile).where(AssetMediaProfile.asset_id == asset_id).limit(1)
            )

    def upsert(
        self,
        *,
        asset_id: UUID,
        pipeline_id: UUID | None,
        project_id: UUID | None,
        analysis: dict,
        embedding: list[float],
        embedding_model: str,
        vision_model: str,
    ) -> AssetMediaProfile:
        with Session(self._engine()) as session:
            row = session.scalar(
                select(AssetMediaProfile).where(AssetMediaProfile.asset_id == asset_id).limit(1)
            )
            if row is None:
                row = AssetMediaProfile(
                    asset_id=asset_id,
                    pipeline_id=pipeline_id,
                    project_id=project_id,
                )
                session.add(row)
            row.pipeline_id = pipeline_id
            row.project_id = project_id
            row.analysis = analysis
            row.embedding = embedding or None
            row.embedding_model = embedding_model or None
            row.vision_model = vision_model or None
            session.commit()
            session.refresh(row)
            return row
