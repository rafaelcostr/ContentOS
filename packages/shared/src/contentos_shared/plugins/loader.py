"""Register default platform plugins and run post_publish hook."""

import os

from contentos_shared.plugins.context import PlatformPublication, PublishContext
from contentos_shared.plugins.platforms.instagram import InstagramReelsPlugin
from contentos_shared.plugins.platforms.tiktok import TikTokPlugin
from contentos_shared.plugins.platforms.youtube import YouTubeShortsPlugin
from contentos_shared.plugins.publish_base import PublishPlugin
from contentos_shared.plugins.registry import PluginRegistry

_loaded = False

_BUILTIN_MAP = {
    "tiktok": TikTokPlugin,
    "youtube": YouTubeShortsPlugin,
    "instagram": InstagramReelsPlugin,
}


def ensure_plugins_loaded() -> PluginRegistry:
    global _loaded
    registry = PluginRegistry.instance()
    if _loaded:
        return registry

    for name, cls in _BUILTIN_MAP.items():
        registry.register(cls())

    try:
        from contentos_plugins_core.application.marketplace import get_marketplace
        from contentos_plugins_core.infrastructure.discovery import discover_installed
        from contentos_plugins_core.infrastructure.loader import load_plugin_instance

        market = get_marketplace()
        for manifest in discover_installed():
            if manifest.name in _BUILTIN_MAP:
                continue
            item = market.get(manifest.name)
            if item and not item.get("installed"):
                continue
            plugin = load_plugin_instance(manifest)
            if plugin:
                registry.register(plugin)
    except ImportError:
        pass

    _loaded = True
    return registry


def get_enabled_platforms() -> list[str]:
    try:
        from contentos_plugins_core.application.marketplace import get_marketplace

        platforms = get_marketplace().enabled_platforms()
        if platforms:
            return platforms
    except ImportError:
        pass
    raw = os.getenv("ENABLED_PLATFORMS", "tiktok,youtube,instagram")
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


def list_publish_plugins() -> list[PublishPlugin]:
    registry = ensure_plugins_loaded()
    return [p for p in registry._plugins.values() if isinstance(p, PublishPlugin)]


async def run_post_publish(context: PublishContext) -> dict[str, dict]:
    """Run all enabled platform plugins — prepare + optional publish."""
    registry = ensure_plugins_loaded()
    enabled = set(get_enabled_platforms())
    mode = os.getenv("PUBLISH_MODE", "dry_run").lower()
    results: dict[str, dict] = {}

    for name in enabled:
        plugin = registry.get(name)
        if not isinstance(plugin, PublishPlugin):
            continue
        prepared = await plugin.prepare(context)
        if mode == "live":
            prepared = await plugin.publish(context, prepared)
        else:
            prepared = await plugin.publish(context, prepared)

        results[name] = prepared.to_dict()

    return results


async def run_single_platform(platform: str, context: PublishContext, force_live: bool = False) -> PlatformPublication:
    registry = ensure_plugins_loaded()
    plugin = registry.get(platform)
    if not isinstance(plugin, PublishPlugin):
        raise ValueError(f"Unknown platform plugin: {platform}")

    prepared = await plugin.prepare(context)
    if force_live or os.getenv("PUBLISH_MODE", "dry_run").lower() == "live":
        return await plugin.publish(context, prepared)
    return await plugin.publish(context, prepared)


def reload_plugins() -> PluginRegistry:
    """Clear registry and reload builtins + installed plugins."""
    global _loaded
    _loaded = False
    PluginRegistry._instance = None
    return ensure_plugins_loaded()
