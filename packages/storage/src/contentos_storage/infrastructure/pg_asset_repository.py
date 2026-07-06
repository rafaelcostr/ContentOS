"""PostgreSQL asset repository."""

from __future__ import annotations

import os
from uuid import UUID

from contentos_database.models import Asset
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


def _sync_url(database_url: str | None = None) -> str:
    url = database_url or os.getenv("DATABASE_URL", "")
    return (
        url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        .replace("postgresql://", "postgresql+psycopg2://")
    )


class PgAssetRepository:
    def __init__(self, session: AsyncSession | None = None, database_url: str | None = None) -> None:
        self._session = session
        self._database_url = database_url

    async def find_by_hash(self, sha256: str) -> Asset | None:
        if not self._session:
            return self.find_by_hash_sync(sha256)
        result = await self._session.execute(select(Asset).where(Asset.sha256 == sha256).limit(1))
        return result.scalar_one_or_none()

    async def save(self, asset: Asset) -> Asset:
        if not self._session:
            return self.save_sync(asset)
        self._session.add(asset)
        await self._session.flush()
        return asset

    def _engine(self):
        return create_engine(_sync_url(self._database_url), pool_pre_ping=True)

    def find_by_hash_sync(self, sha256: str) -> Asset | None:
        if not sha256:
            return None
        with Session(self._engine()) as session:
            return session.scalar(select(Asset).where(Asset.sha256 == sha256).limit(1))

    def save_sync(self, asset: Asset) -> Asset:
        with Session(self._engine()) as session:
            session.add(asset)
            session.commit()
            session.refresh(asset)
            return asset

    def get_sync(self, asset_id: UUID) -> Asset | None:
        with Session(self._engine()) as session:
            return session.get(Asset, asset_id)
