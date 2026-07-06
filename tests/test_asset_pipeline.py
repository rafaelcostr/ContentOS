"""Tests for Asset Pipeline Service (Phase 8)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from contentos_database.models import Asset
from contentos_shared.enums import AssetCategory
from contentos_shared.schemas.asset import AssetMeta, AssetRef
from contentos_storage.application.asset_index_service import AssetIndexService
from contentos_storage.application.asset_pipeline_service import AssetPipelineService, tags_from_meta


def test_tags_from_meta():
    meta = AssetMeta(tags={"source": "local_library", "scene": "intro"})
    tags = tags_from_meta(meta, extra=["indexed"])
    assert "source:local_library" in tags
    assert "scene:intro" in tags
    assert "indexed" in tags


@pytest.mark.asyncio
async def test_store_and_persist_creates_asset_row():
    data = b"fake-video-bytes"
    sha = AssetIndexService.compute_hash(data)
    project_id = uuid4()
    pipeline_id = uuid4()

    manager = AsyncMock()
    manager.store.return_value = AssetRef(
        id=uuid4(),
        category=AssetCategory.TAKES,
        key="takes/abc.mp4",
        bucket="contentos",
        content_type="video/mp4",
        size_bytes=len(data),
    )

    repo = MagicMock()
    repo.find_by_hash_sync.return_value = None
    repo.save_sync.side_effect = lambda asset: asset

    service = AssetPipelineService(manager, repository=repo)
    meta = AssetMeta(project_id=project_id, pipeline_id=pipeline_id, filename="clip.mp4", content_type="video/mp4")
    result = await service.store_and_persist(AssetCategory.TAKES, data, meta, extra_tags=["scene_1"])

    assert result.deduplicated is False
    assert result.asset_id == manager.store.return_value.id
    repo.save_sync.assert_called_once()
    saved: Asset = repo.save_sync.call_args[0][0]
    assert saved.sha256 == sha
    assert saved.object_key == "takes/abc.mp4"


@pytest.mark.asyncio
async def test_store_and_persist_reuses_existing_hash():
    data = b"duplicate"
    existing_id = uuid4()
    existing = Asset(
        id=existing_id,
        category=AssetCategory.TAKES.value,
        bucket="contentos",
        object_key="takes/existing.mp4",
        content_type="video/mp4",
        size_bytes=len(data),
        sha256=AssetIndexService.compute_hash(data),
    )

    manager = AsyncMock()
    repo = MagicMock()
    repo.find_by_hash_sync.return_value = existing

    service = AssetPipelineService(manager, repository=repo)
    meta = AssetMeta(filename="clip.mp4", content_type="video/mp4")
    result = await service.store_and_persist(AssetCategory.TAKES, data, meta)

    assert result.deduplicated is True
    assert result.asset_id == existing_id
    manager.store.assert_not_called()


def test_index_assets_sync_tags_rows():
    asset_id = uuid4()
    pipeline_id = uuid4()
    asset = Asset(
        id=asset_id,
        category=AssetCategory.TAKES.value,
        bucket="contentos",
        object_key="takes/a.mp4",
        content_type="video/mp4",
        size_bytes=100,
        tags=["scene_1"],
    )

    repo = MagicMock()
    repo.get_sync.return_value = asset
    repo.save_sync.side_effect = lambda row: row

    service = AssetPipelineService(AsyncMock(), repository=repo)
    indexed = service.index_assets_sync([str(asset_id)], pipeline_id)

    assert indexed == 1
    assert "indexed" in asset.tags
    assert f"pipeline:{pipeline_id}" in asset.tags
