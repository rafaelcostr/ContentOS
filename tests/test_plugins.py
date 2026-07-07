"""Platform plugin unit tests."""

import os
from uuid import uuid4

import httpx
import pytest
from contentos_shared.plugins.context import PublishContext
from contentos_shared.plugins.loader import ensure_plugins_loaded, get_enabled_platforms, run_post_publish
from contentos_shared.plugins.platforms.instagram import InstagramReelsPlugin
from contentos_shared.plugins.platforms.tiktok import TikTokPlugin
from contentos_shared.plugins.platforms.youtube import YouTubeShortsPlugin
from contentos_shared.plugins.registry import PluginRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    PluginRegistry._instance = None
    import contentos_shared.plugins.loader as loader_mod

    loader_mod._loaded = False
    yield
    PluginRegistry._instance = None
    loader_mod._loaded = False


def _context(**overrides):
    defaults = {
        "pipeline_id": uuid4(),
        "project_id": uuid4(),
        "topic": "GTA 6",
        "script": {"title": "GTA 6", "full_text": "test"},
        "base_metadata": {
            "title": "GTA 6 vai ser INSANO",
            "description": "Tudo sobre o lançamento",
            "hashtags": ["gta6", "gaming", "viral"],
        },
        "render_ref": {"key": "renders/test.mp4"},
        "render_bytes": b"fake-mp4-bytes",
    }
    defaults.update(overrides)
    return PublishContext(**defaults)


@pytest.mark.asyncio
async def test_tiktok_prepare_truncates_title():
    plugin = TikTokPlugin()
    ctx = _context(base_metadata={"title": "x" * 200, "description": "d", "hashtags": ["a"]})
    result = await plugin.prepare(ctx)
    assert result.platform == "tiktok"
    assert len(result.title) <= 150
    assert len(result.hashtags) <= 5


@pytest.mark.asyncio
async def test_youtube_adds_shorts_hashtag():
    plugin = YouTubeShortsPlugin()
    result = await plugin.prepare(_context())
    assert any("shorts" in h.lower() for h in result.hashtags)
    assert result.payload.get("is_short") is True


@pytest.mark.asyncio
async def test_instagram_prepare_caption():
    plugin = InstagramReelsPlugin()
    result = await plugin.prepare(_context())
    assert result.platform == "instagram"
    assert len(result.description) <= 2200
    assert result.payload.get("media_type") == "REELS"


@pytest.mark.asyncio
async def test_dry_run_publish(monkeypatch):
    monkeypatch.setenv("PUBLISH_MODE", "dry_run")
    plugin = TikTokPlugin()
    prepared = await plugin.prepare(_context())
    published = await plugin.publish(_context(), prepared)
    assert published.status == "dry_run"
    assert published.publish_url is not None


@pytest.mark.asyncio
async def test_prepare_only_publish_mode(monkeypatch):
    monkeypatch.setenv("PUBLISH_MODE", "prepare_only")
    plugin = TikTokPlugin()
    prepared = await plugin.prepare(_context())
    published = await plugin.publish(_context(), prepared)
    assert published.status == "ready"
    assert published.payload["mode"] == "prepare_only"


@pytest.mark.asyncio
async def test_live_publish_missing_credentials_fails(monkeypatch):
    monkeypatch.setenv("PUBLISH_MODE", "live")
    plugin = TikTokPlugin()
    prepared = await plugin.prepare(_context(credentials={}))
    published = await plugin.publish(_context(credentials={}), prepared)
    assert published.status == "failed"
    assert "credentials" in published.error


@pytest.mark.asyncio
async def test_youtube_live_upload_completes_resumable(monkeypatch):
    monkeypatch.setenv("PUBLISH_MODE", "live")
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "POST":
            return httpx.Response(200, headers={"Location": "https://upload.youtube.test/session"})
        if request.method == "PUT":
            assert request.content == b"fake-mp4-bytes"
            return httpx.Response(200, json={"id": "yt123"})
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: real_client(transport=transport))

    plugin = YouTubeShortsPlugin()
    ctx = _context(credentials={"youtube": {"access_token": "token"}})
    prepared = await plugin.prepare(ctx)
    published = await plugin.publish(ctx, prepared)
    assert calls == ["POST", "PUT"]
    assert published.status == "published"
    assert published.external_id == "yt123"
    assert published.publish_url == "https://www.youtube.com/watch?v=yt123"


@pytest.mark.asyncio
async def test_youtube_chunked_resumable_upload(monkeypatch):
    monkeypatch.setenv("PUBLISH_MODE", "live")
    chunk_headers: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, headers={"Location": "https://upload.youtube.test/session"})
        if request.method == "PUT":
            chunk_headers.append(request.headers.get("Content-Range", "full"))
            if request.headers.get("Content-Range", "").startswith("bytes 0-"):
                return httpx.Response(308, headers={"Range": "bytes=0-5242879"})
            return httpx.Response(200, json={"id": "yt-chunk"})
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: real_client(transport=transport))

    plugin = YouTubeShortsPlugin()
    large = b"x" * (5 * 1024 * 1024 + 1024)
    ctx = _context(render_bytes=large, credentials={"youtube": {"access_token": "token"}})
    prepared = await plugin.prepare(ctx)
    published = await plugin.publish(ctx, prepared)
    assert published.status == "published"
    assert published.external_id == "yt-chunk"
    assert len(chunk_headers) >= 2


@pytest.mark.asyncio
async def test_instagram_live_uses_render_public_url(monkeypatch):
    monkeypatch.setenv("PUBLISH_MODE", "live")
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/media"):
            return httpx.Response(200, json={"id": "container1"})
        if request.url.path.endswith("/media_publish"):
            return httpx.Response(200, json={"id": "reel1"})
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: real_client(transport=transport))

    plugin = InstagramReelsPlugin()
    ctx = _context(
        render_public_url="https://cdn.example.com/renders/demo.mp4",
        credentials={"instagram": {"access_token": "token", "instagram_user_id": "ig1"}},
    )
    prepared = await plugin.prepare(ctx)
    published = await plugin.publish(ctx, prepared)
    assert published.status == "published"
    assert published.external_id == "reel1"
    assert calls


@pytest.mark.asyncio
async def test_instagram_live_requires_public_video_url(monkeypatch):
    monkeypatch.setenv("PUBLISH_MODE", "live")
    plugin = InstagramReelsPlugin()
    ctx = _context(credentials={"instagram": {"access_token": "token", "instagram_user_id": "ig1"}})
    prepared = await plugin.prepare(ctx)
    published = await plugin.publish(ctx, prepared)
    assert published.status == "failed"
    assert "video_url" in published.error


@pytest.mark.asyncio
async def test_run_post_publish_all_platforms(monkeypatch):
    monkeypatch.setenv("PUBLISH_MODE", "dry_run")
    monkeypatch.setenv("ENABLED_PLATFORMS", "tiktok,youtube,instagram")
    ensure_plugins_loaded()
    results = await run_post_publish(_context())
    assert set(results.keys()) == {"tiktok", "youtube", "instagram"}
    assert all(r["status"] == "dry_run" for r in results.values())


def test_get_enabled_platforms(monkeypatch):
    monkeypatch.setenv("ENABLED_PLATFORMS", "tiktok, youtube")
    assert get_enabled_platforms() == ["tiktok", "youtube"]
