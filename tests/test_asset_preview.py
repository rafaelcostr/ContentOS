"""Tier A3 — asset preview helpers."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from contentos_database.models import Asset
from contentos_gateway.services.asset_service import AssetService
from contentos_shared.enums import AssetCategory


def test_preview_kind():
    assert AssetService.preview_kind("image/jpeg") == "image"
    assert AssetService.preview_kind("video/mp4") == "video"
    assert AssetService.preview_kind("audio/mpeg") == "audio"
    assert AssetService.preview_kind("application/json") == "other"


def test_public_presigned_url_rewrite(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT", "localhost:9000")
    url = "http://minio:9000/contentos/takes/abc.mp4?X-Amz-Signature=1"
    assert AssetService._public_presigned_url(url) == "http://localhost:9000/contentos/takes/abc.mp4?X-Amz-Signature=1"


def _service_with_mocks(session, manager) -> AssetService:
    service = AssetService.__new__(AssetService)
    service.session = session
    service.manager = manager
    return service


@pytest.mark.asyncio
async def test_get_preview_returns_presigned_url(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT", "localhost:9000")

    asset_id = uuid4()
    asset = Asset(
        id=asset_id,
        category=AssetCategory.TAKES.value,
        bucket="contentos",
        object_key="takes/demo.mp4",
        content_type="video/mp4",
        size_bytes=100,
    )

    session = AsyncMock()
    session.get = AsyncMock(return_value=asset)
    manager = MagicMock()
    manager.exists = AsyncMock(return_value=True)
    manager.get_presigned_url = AsyncMock(return_value="http://minio:9000/contentos/takes/demo.mp4?sig=1")
    service = _service_with_mocks(session, manager)

    preview = await service.get_preview(asset_id)
    assert preview is not None
    assert preview["available"] is True
    assert preview["kind"] == "video"
    assert preview["url"].startswith("http://localhost:9000/")


@pytest.mark.asyncio
async def test_get_preview_missing_object():
    asset_id = uuid4()
    asset = Asset(
        id=asset_id,
        category=AssetCategory.TAKES.value,
        bucket="contentos",
        object_key="takes/missing.mp4",
        content_type="video/mp4",
        size_bytes=0,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=asset)
    manager = MagicMock()
    manager.exists = AsyncMock(return_value=False)
    service = _service_with_mocks(session, manager)

    preview = await service.get_preview(asset_id)
    assert preview["available"] is False
    assert preview["url"] is None
