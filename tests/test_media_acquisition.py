"""Tests for V5.0 media acquisition — Pexels, Pixabay, DownloadPipeline."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from contentos_sources.application.download_pipeline import DownloadPipeline, DownloadTooLargeError
from contentos_sources.application.source_manager import SourceManager, get_source_manager
from contentos_sources.domain.media_license import ROYALTY_FREE, is_license_allowed
from contentos_sources.domain.source_query import SourceQuery
from contentos_sources.infrastructure.factory import build_registry

PEXELS_SEARCH_JSON = {
    "videos": [
        {
            "id": 1001,
            "duration": 12,
            "url": "https://www.pexels.com/video/1001/",
            "image": "https://images.pexels.com/preview.jpg",
            "user": {"name": "Test User"},
            "video_files": [
                {
                    "id": 1,
                    "quality": "hd",
                    "file_type": "video/mp4",
                    "width": 1080,
                    "height": 1920,
                    "link": "https://cdn.example/1001.mp4",
                },
            ],
        }
    ]
}

PEXELS_VIDEO_JSON = {
    "id": 1001,
    "url": "https://www.pexels.com/video/1001/",
    "user": {"name": "Test User"},
    "video_files": [
        {"file_type": "video/mp4", "width": 1080, "height": 1920, "link": "https://cdn.example/1001.mp4"},
    ],
}

PIXABAY_SEARCH_JSON = {
    "hits": [
        {
            "id": 2002,
            "duration": 15,
            "tags": "gta car city night",
            "pageURL": "https://pixabay.com/videos/2002/",
            "videos": {
                "large": {"url": "https://cdn.example/2002_large.mp4", "width": 1920, "height": 1080},
            },
        }
    ]
}

PIXABAY_ID_JSON = {
    "hits": [
        {
            "id": 2002,
            "tags": "gta car",
            "pageURL": "https://pixabay.com/videos/2002/",
            "videos": {"large": {"url": "https://cdn.example/2002_large.mp4"}},
        }
    ]
}

FAKE_MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 128

_REAL_HTTPX_CLIENT = httpx.AsyncClient


def _mock_client_factory(handler):
    transport = httpx.MockTransport(handler)

    def factory(*_args, **_kwargs):
        return _REAL_HTTPX_CLIENT(transport=transport)

    return factory


def _fresh_manager() -> SourceManager:
    get_source_manager.cache_clear()
    mgr = SourceManager()
    mgr._registry = build_registry()
    return mgr


def _mock_public_dns(monkeypatch) -> None:
    def fake_getaddrinfo(host, port, *args, **kwargs):
        if host == "cdn.example":
            return [(None, None, None, "", ("93.184.216.34", port or 443))]
        raise OSError(f"unexpected DNS lookup: {host}")

    monkeypatch.setattr("contentos_sources.application.download_pipeline.socket.getaddrinfo", fake_getaddrinfo)


@pytest.mark.asyncio
async def test_pexels_search_mocked(monkeypatch):
    monkeypatch.setenv("CONTENT_SOURCES_ENABLED", "pexels")
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        if "/videos/search" in str(request.url):
            return httpx.Response(200, json=PEXELS_SEARCH_JSON)
        return httpx.Response(404)

    factory = _mock_client_factory(handler)
    monkeypatch.setattr("contentos_sources.adapters.pexels.httpx.AsyncClient", factory)

    mgr = _fresh_manager()
    query = SourceQuery(scene_description="car chase city", topic="GTA 6", tags=["car"])
    results = await mgr.search(query, source_id="pexels")
    assert len(results) == 1
    assert results[0].source_id == "pexels"
    assert results[0].candidate_id == "1001"
    assert results[0].metadata["license_type"] == ROYALTY_FREE


@pytest.mark.asyncio
async def test_pexels_fetch_mocked(monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setenv("MEDIA_ALLOWED_LICENSES", "royalty_free")
    _mock_public_dns(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/videos/1001"):
            return httpx.Response(200, json=PEXELS_VIDEO_JSON)
        if "cdn.example" in url:
            return httpx.Response(200, content=FAKE_MP4, headers={"content-type": "video/mp4"})
        return httpx.Response(404)

    factory = _mock_client_factory(handler)
    monkeypatch.setattr("contentos_sources.adapters.pexels.httpx.AsyncClient", factory)
    monkeypatch.setattr("contentos_sources.application.download_pipeline.httpx.AsyncClient", factory)

    from contentos_sources.adapters.pexels import PexelsSource

    asset = await PexelsSource().fetch("1001")
    assert asset.source_id == "pexels"
    assert len(asset.data) > 50
    assert asset.sha256
    assert asset.metadata["license_type"] == ROYALTY_FREE


@pytest.mark.asyncio
async def test_pixabay_search_and_fetch_mocked(monkeypatch):
    monkeypatch.setenv("PIXABAY_API_KEY", "pix-key")
    monkeypatch.setenv("MEDIA_ALLOWED_LICENSES", "royalty_free")
    _mock_public_dns(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "pixabay.com" in url and "id=2002" in url:
            return httpx.Response(200, json=PIXABAY_ID_JSON)
        if "pixabay.com" in url:
            return httpx.Response(200, json=PIXABAY_SEARCH_JSON)
        if "cdn.example" in url:
            return httpx.Response(200, content=FAKE_MP4, headers={"content-type": "video/mp4"})
        return httpx.Response(404)

    factory = _mock_client_factory(handler)
    monkeypatch.setattr("contentos_sources.adapters.pixabay.httpx.AsyncClient", factory)
    monkeypatch.setattr("contentos_sources.application.download_pipeline.httpx.AsyncClient", factory)

    from contentos_sources.adapters.pixabay import PixabaySource

    src = PixabaySource()
    query = SourceQuery(scene_description="night city", topic="GTA 6")
    found = await src.search(query)
    assert found[0].candidate_id == "2002"
    asset = await src.fetch("2002")
    assert asset.filename.startswith("pixabay_")


@pytest.mark.asyncio
async def test_download_pipeline_size_limit(monkeypatch):
    monkeypatch.setenv("MEDIA_MAX_DOWNLOAD_MB", "0.000001")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 8000, headers={"content-type": "video/mp4"})

    factory = _mock_client_factory(handler)
    monkeypatch.setattr("contentos_sources.application.download_pipeline.httpx.AsyncClient", factory)

    pipeline = DownloadPipeline()
    with pytest.raises(DownloadTooLargeError):
        await pipeline.download("https://example.com/big.mp4")


def test_license_validation(monkeypatch):
    monkeypatch.setenv("MEDIA_ALLOWED_LICENSES", "royalty_free")
    assert is_license_allowed(ROYALTY_FREE) is True
    assert is_license_allowed("preview_only") is False


@pytest.mark.asyncio
async def test_search_all_scenes_with_pexels(monkeypatch):
    monkeypatch.setenv("CONTENT_SOURCES_ENABLED", "pexels")
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=PEXELS_SEARCH_JSON)

    factory = _mock_client_factory(handler)
    monkeypatch.setattr("contentos_sources.adapters.pexels.httpx.AsyncClient", factory)

    mgr = _fresh_manager()
    scenes = [{"label": "intro", "description": "car chase", "visual_hint": "city night"}]
    rows = await mgr.search_all_scenes(scenes, uuid4(), "GTA 6")
    assert len(rows) == 1
    assert len(rows[0]["candidates"]) >= 1


def test_pixabay_prefers_portrait_url():
    from contentos_sources.adapters.pixabay import _best_pixabay_url

    url = _best_pixabay_url(
        {
            "large": {"url": "https://example.com/landscape.mp4", "width": 1920, "height": 1080},
            "medium": {"url": "https://example.com/portrait.mp4", "width": 720, "height": 1280},
        }
    )
    assert url == "https://example.com/portrait.mp4"


def test_factory_registers_pexels_pixabay():
    registry = build_registry()
    assert registry.get("pexels") is not None
    assert registry.get("pixabay") is not None
