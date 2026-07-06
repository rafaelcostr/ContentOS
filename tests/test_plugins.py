"""Platform plugin unit tests."""

import os
from uuid import uuid4

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
