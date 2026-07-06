"""Asset pipeline — MinIO store + PostgreSQL persist with global hash dedup."""

from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID

from contentos_database.models import Asset
from contentos_shared.enums import AssetCategory
from contentos_shared.schemas.asset import AssetMeta, AssetRef
from contentos_storage.application.asset_index_service import AssetIndexService
from contentos_storage.domain.asset_manager import AssetManager
from contentos_storage.domain.asset_metadata import facet_tags
from contentos_storage.infrastructure.pg_asset_repository import PgAssetRepository


@dataclass(frozen=True)
class PersistedAsset:
    ref: AssetRef
    asset_id: UUID
    deduplicated: bool


def tags_from_meta(
    meta: AssetMeta,
    extra: list[str] | None = None,
    metadata: dict | None = None,
) -> list[str]:
    tags = list(extra or [])
    for key, value in (meta.tags or {}).items():
        tag = f"{key}:{value}" if value else key
        if tag not in tags:
            tags.append(tag)
    for tag in facet_tags(metadata):
        if tag not in tags:
            tags.append(tag)
    return tags


class AssetPipelineService:
    """Store bytes in object storage and register Asset rows for pipeline agents."""

    def __init__(
        self,
        manager: AssetManager,
        database_url: str | None = None,
        repository: PgAssetRepository | None = None,
    ) -> None:
        self.manager = manager
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self.repository = repository or PgAssetRepository(database_url=self.database_url)

    async def store_and_persist(
        self,
        category: AssetCategory,
        data: bytes,
        meta: AssetMeta,
        *,
        extra_tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> PersistedAsset:
        sha256 = AssetIndexService.compute_hash(data)
        existing = self.repository.find_by_hash_sync(sha256)
        if existing:
            return PersistedAsset(
                ref=self._ref_from_asset(existing),
                asset_id=existing.id,
                deduplicated=True,
            )

        ref = await self.manager.store(category, data, meta)
        meta_payload = metadata or {}
        asset = Asset(
            id=ref.id,
            project_id=meta.project_id,
            pipeline_id=meta.pipeline_id,
            category=category.value,
            bucket=ref.bucket,
            object_key=ref.key,
            content_type=ref.content_type,
            size_bytes=ref.size_bytes,
            sha256=sha256,
            tags=tags_from_meta(meta, extra_tags, meta_payload),
            metadata_=meta_payload,
        )
        saved = self.repository.save_sync(asset)
        return PersistedAsset(
            ref=AssetRef(
                id=saved.id,
                category=category,
                key=saved.object_key,
                bucket=saved.bucket,
                content_type=saved.content_type,
                size_bytes=saved.size_bytes,
            ),
            asset_id=saved.id,
            deduplicated=False,
        )

    def index_assets_sync(self, asset_ids: list[str], pipeline_id: UUID) -> int:
        indexed = 0
        for raw_id in asset_ids:
            try:
                asset_id = UUID(raw_id)
            except ValueError:
                continue
            asset = self.repository.get_sync(asset_id)
            if not asset:
                continue
            tags = list(asset.tags or [])
            for tag in ("indexed", f"pipeline:{pipeline_id}"):
                if tag not in tags:
                    tags.append(tag)
            asset.tags = tags
            self.repository.save_sync(asset)
            indexed += 1
        return indexed

    @staticmethod
    def _ref_from_asset(asset: Asset) -> AssetRef:
        return AssetRef(
            id=asset.id,
            category=AssetCategory(asset.category),
            key=asset.object_key,
            bucket=asset.bucket,
            content_type=asset.content_type,
            size_bytes=asset.size_bytes,
        )
