"""Tests for Plugin Marketplace (V2.9)."""

import shutil
from pathlib import Path

import pytest

REPO_PLUGINS = Path(__file__).resolve().parents[1] / "plugins"


@pytest.fixture(autouse=True)
def plugins_env(monkeypatch, tmp_path):
    dest = tmp_path / "plugins"
    shutil.copytree(REPO_PLUGINS, dest)
    monkeypatch.setenv("PLUGINS_ROOT", str(dest))
    monkeypatch.setenv("DATABASE_URL", "")
    import contentos_shared.plugins.loader as loader_mod
    from contentos_plugins_core.application.marketplace import get_marketplace
    from contentos_shared.plugins.registry import PluginRegistry

    PluginRegistry._instance = None
    loader_mod._loaded = False
    get_marketplace.cache_clear()
    yield
    PluginRegistry._instance = None
    loader_mod._loaded = False
    get_marketplace.cache_clear()


def test_discover_marketplace_includes_builtin_and_optional():
    from contentos_plugins_core.infrastructure.discovery import discover_marketplace

    names = {m.name for m in discover_marketplace()}
    assert "tiktok" in names
    assert "telegram" in names
    assert "discord" in names
    assert "wordpress" in names


def test_marketplace_catalog():
    from contentos_plugins_core import get_marketplace

    catalog = get_marketplace().catalog()
    assert len(catalog) >= 6
    tiktok = next(p for p in catalog if p["name"] == "tiktok")
    assert tiktok["builtin"] is True
    assert tiktok["installed"] is True
    telegram = next(p for p in catalog if p["name"] == "telegram")
    assert telegram["builtin"] is False
    assert telegram["installed"] is False


def test_install_telegram_plugin():
    from contentos_plugins_core import get_marketplace
    from contentos_plugins_core.infrastructure.discovery import installed_plugin_path

    market = get_marketplace()
    item = market.install("telegram")
    assert item["installed"] is True
    assert installed_plugin_path("telegram") is not None


def test_load_installed_telegram_plugin():
    from contentos_plugins_core import get_marketplace
    from contentos_plugins_core.infrastructure.discovery import discover_installed
    from contentos_plugins_core.infrastructure.loader import load_plugin_instance
    from contentos_shared.plugins.publish_base import PublishPlugin

    get_marketplace().install("telegram")
    manifest = next(m for m in discover_installed() if m.name == "telegram")
    plugin = load_plugin_instance(manifest)
    assert isinstance(plugin, PublishPlugin)
    assert plugin.platform == "telegram"


def test_enable_plugin_updates_platforms(monkeypatch):
    from contentos_plugins_core import get_marketplace

    market = get_marketplace()
    market.install("telegram")
    market.set_enabled("telegram", True)
    monkeypatch.setenv("ENABLED_PLATFORMS", "")
    from contentos_shared.plugins.loader import get_enabled_platforms

    platforms = get_enabled_platforms()
    assert "telegram" in platforms


def test_cannot_uninstall_builtin():
    from contentos_plugins_core import get_marketplace

    with pytest.raises(ValueError, match="builtin"):
        get_marketplace().uninstall("tiktok")
