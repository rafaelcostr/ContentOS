"""Asset service — Gateway layer over Asset Manager."""

import os
from uuid import UUID

from contentos_database.models import Asset
from contentos_shared.enums import AssetCategory
from contentos_shared.schemas.asset import AssetMeta, AssetRef
from contentos_storage.application.asset_index_service import AssetIndexService, AssetSearchFilters
from contentos_storage.domain.asset_metadata import facet_tags, normalize_asset_metadata
from contentos_storage.factory import StorageSettings, get_asset_manager
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _storage_settings() -> StorageSettings:
    return StorageSettings(
        endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "contentos"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "contentos_secret"),
        bucket=os.getenv("MINIO_BUCKET", "contentos"),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
    )


class AssetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.manager = get_asset_manager(_storage_settings())

    async def upload_take(
        self,
        data: bytes,
        filename: str,
        theme: str,
        label: str,
        project_id: UUID | None = None,
    ) -> Asset:
        meta = AssetMeta(
            project_id=project_id,
            filename=filename or f"{label}.mp4",
            content_type="video/mp4",
            tags={"theme": theme, "label": label},
        )
        ref = await self.manager.store(AssetCategory.TAKES, data, meta)
        index = AssetIndexService(self.session)
        sha = index.compute_hash(data)
        existing = await index.find_by_hash(sha)
        if existing:
            return existing

        search_meta = normalize_asset_metadata(
            topic=theme,
            extra={"theme": theme, "label": label, "game": theme},
        )
        tags = [theme, label, *facet_tags(search_meta)]
        asset = Asset(
            id=ref.id,
            project_id=project_id,
            category=AssetCategory.TAKES.value,
            bucket=ref.bucket,
            object_key=ref.key,
            content_type=ref.content_type,
            size_bytes=ref.size_bytes,
            sha256=sha,
            tags=tags,
            metadata_=search_meta,
        )
        self.session.add(asset)
        await self.session.flush()
        return asset

    async def search_assets(
        self,
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
        return await AssetIndexService(self.session).search_filters(filters)

    async def tag_asset(self, asset_id: UUID, tags: list[str]) -> Asset | None:
        return await AssetIndexService(self.session).tag_asset(asset_id, tags)

    async def index_stats(self) -> dict:
        return await AssetIndexService(self.session).dedup_stats()

    async def list_assets(self, category: str | None = None, limit: int = 100) -> list[Asset]:
        query = select(Asset).order_by(Asset.created_at.desc()).limit(limit)
        if category:
            query = query.where(Asset.category == category)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def storage_stats(self) -> dict:
        total = await self.session.scalar(select(func.count()).select_from(Asset))
        by_category = await self.session.execute(
            select(Asset.category, func.count(), func.sum(Asset.size_bytes)).group_by(Asset.category)
        )
        categories = {row[0]: {"count": row[1], "size_bytes": row[2] or 0} for row in by_category.all()}
        total_bytes = sum(c["size_bytes"] for c in categories.values())
        return {
            "total_assets": total or 0,
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "by_category": categories,
        }

    async def get_asset(self, asset_id: UUID) -> Asset | None:
        return await self.session.get(Asset, asset_id)

    def _to_ref(self, asset: Asset) -> AssetRef:
        try:
            category = AssetCategory(asset.category)
        except ValueError:
            category = AssetCategory.ASSETS
        return AssetRef(
            id=asset.id,
            category=category,
            key=asset.object_key,
            bucket=asset.bucket,
            content_type=asset.content_type,
            size_bytes=asset.size_bytes,
        )

    @staticmethod
    def preview_kind(content_type: str) -> str:
        if content_type.startswith("image/"):
            return "image"
        if content_type.startswith("video/"):
            return "video"
        if content_type.startswith("audio/"):
            return "audio"
        return "other"

    @staticmethod
    def _public_presigned_url(url: str) -> str:
        """Rewrite internal MinIO host so browsers can load the URL."""
        internal = os.getenv("MINIO_ENDPOINT", "minio:9000")
        public = os.getenv("MINIO_PUBLIC_ENDPOINT", "localhost:9000")
        if internal == public:
            return url
        for scheme in ("http://", "https://"):
            url = url.replace(f"{scheme}{internal}", f"{scheme}{public}")
        return url

    async def get_preview(self, asset_id: UUID, expires: int = 3600) -> dict | None:
        asset = await self.get_asset(asset_id)
        if not asset:
            return None
        ref = self._to_ref(asset)
        if not await self.manager.exists(ref):
            return {
                "asset_id": str(asset.id),
                "url": None,
                "content_type": asset.content_type,
                "expires_in": expires,
                "kind": self.preview_kind(asset.content_type),
                "available": False,
                "error": "object missing in storage",
            }
        url = await self.manager.get_presigned_url(ref, expires=expires)
        return {
            "asset_id": str(asset.id),
            "url": self._public_presigned_url(url),
            "content_type": asset.content_type,
            "expires_in": expires,
            "kind": self.preview_kind(asset.content_type),
            "available": True,
            "error": None,
        }

    async def get_content(self, asset_id: UUID) -> tuple[Asset, bytes] | None:
        asset = await self.get_asset(asset_id)
        if not asset:
            return None
        ref = self._to_ref(asset)
        data = await self.manager.get(ref)
        return asset, data

