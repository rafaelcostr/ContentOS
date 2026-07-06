"""Asset Manager V2 — index, search, tags, hash dedup."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from contentos_database.models import Asset
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class AssetSearchFilters:
    q: str | None = None
    category: str | None = None
    tag: str | None = None
    theme: str | None = None
    game: str | None = None
    character: str | None = None
    motion: str | None = None
    color: str | None = None
    objects: str | None = None
    limit: int = 50


class AssetIndexService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def compute_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    async def find_by_hash(self, sha256: str) -> Asset | None:
        result = await self.session.execute(select(Asset).where(Asset.sha256 == sha256).limit(1))
        return result.scalar_one_or_none()

    async def index_asset(
        self,
        asset: Asset,
        *,
        data: bytes | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> Asset:
        if data is not None:
            asset.sha256 = self.compute_hash(data)
        if tags:
            existing = list(asset.tags or [])
            for t in tags:
                if t not in existing:
                    existing.append(t)
            asset.tags = existing
        if metadata:
            merged = dict(asset.metadata_ or {})
            merged.update(metadata)
            asset.metadata_ = merged
        await self.session.flush()
        return asset

    async def search(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        tag: str | None = None,
        theme: str | None = None,
        game: str | None = None,
        character: str | None = None,
        motion: str | None = None,
        color: str | None = None,
        objects: str | None = None,
        limit: int = 50,
    ) -> list[Asset]:
        filters = AssetSearchFilters(
            q=q,
            category=category,
            tag=tag,
            theme=theme,
            game=game,
            character=character,
            motion=motion,
            color=color,
            objects=objects,
            limit=limit,
        )
        return await self.search_filters(filters)

    async def search_filters(self, filters: AssetSearchFilters) -> list[Asset]:
        query = select(Asset).order_by(Asset.created_at.desc()).limit(min(filters.limit, 200))
        if filters.category:
            query = query.where(Asset.category == filters.category)
        if filters.tag:
            query = query.where(Asset.tags.contains([filters.tag]))

        for key, value in (
            ("theme", filters.theme),
            ("game", filters.game),
            ("character", filters.character),
            ("motion", filters.motion),
            ("color", filters.color),
        ):
            if value:
                query = query.where(self._facet_clause(key, value))

        if filters.objects:
            query = query.where(self._objects_clause(filters.objects))

        if filters.q:
            pattern = f"%{filters.q}%"
            query = query.where(
                or_(
                    Asset.object_key.ilike(pattern),
                    Asset.content_type.ilike(pattern),
                    Asset.metadata_["theme"].as_string().ilike(pattern),
                    Asset.metadata_["game"].as_string().ilike(pattern),
                    Asset.metadata_["character"].as_string().ilike(pattern),
                    Asset.metadata_["motion"].as_string().ilike(pattern),
                    Asset.metadata_["color"].as_string().ilike(pattern),
                    Asset.metadata_["objects"].as_string().ilike(pattern),
                    Asset.metadata_["label"].as_string().ilike(pattern),
                    Asset.metadata_["scene_label"].as_string().ilike(pattern),
                )
            )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def _facet_clause(key: str, value: str):
        pattern = f"%{value}%"
        return or_(
            Asset.metadata_[key].as_string().ilike(pattern),
            Asset.tags.contains([f"{key}:{value}"]),
            Asset.tags.contains([value]),
        )

    @staticmethod
    def _objects_clause(value: str):
        pattern = f"%{value}%"
        return or_(
            Asset.metadata_["objects"].as_string().ilike(pattern),
            Asset.tags.contains([f"object:{value}"]),
            Asset.tags.contains([value]),
        )

    async def tag_asset(self, asset_id: UUID, tags: list[str]) -> Asset | None:
        asset = await self.session.get(Asset, asset_id)
        if not asset:
            return None
        return await self.index_asset(asset, tags=tags)

    async def dedup_stats(self) -> dict:
        from sqlalchemy import func

        total = await self.session.scalar(select(func.count()).select_from(Asset)) or 0
        hashed = await self.session.scalar(select(func.count()).select_from(Asset).where(Asset.sha256.isnot(None))) or 0
        return {"total_assets": total, "indexed_hashes": hashed}
