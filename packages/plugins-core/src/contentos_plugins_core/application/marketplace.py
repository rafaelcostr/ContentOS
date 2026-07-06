"""Plugin marketplace catalog and install state."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from contentos_plugins_core.domain.plugin_manifest import PluginManifest
from contentos_plugins_core.infrastructure.discovery import discover_installed, discover_marketplace
from contentos_plugins_core.infrastructure.repository import PluginStateRepository

BUILTIN_PLUGINS = ("tiktok", "youtube", "instagram")


class PluginMarketplace:
    def __init__(self) -> None:
        self._repo = PluginStateRepository()

    def catalog(self) -> list[dict[str, Any]]:
        """All plugins available in marketplace with install/enable status."""
        market = {m.name: m for m in discover_marketplace()}
        installed = {m.name: m for m in discover_installed()}
        states = self._repo.load_all()

        names = sorted(set(market.keys()) | set(installed.keys()) | set(BUILTIN_PLUGINS))
        items: list[dict[str, Any]] = []
        for name in names:
            manifest = market.get(name) or installed.get(name)
            if not manifest and name in BUILTIN_PLUGINS:
                manifest = PluginManifest(
                    name=name,
                    version="1.0.0",
                    description=f"Builtin {name} publish plugin",
                    hooks=["post_publish"],
                    platform=name,
                    builtin=True,
                )
            if not manifest:
                continue
            state = states.get(name, {})
            is_builtin = manifest.builtin or name in BUILTIN_PLUGINS
            is_installed = is_builtin or name in installed or state.get("installed", False)
            items.append(
                {
                    **manifest.to_dict(),
                    "installed": is_installed,
                    "enabled": state.get("enabled", is_builtin and name in self._default_enabled()),
                    "source": "builtin" if is_builtin else "marketplace",
                }
            )
        return items

    def get(self, name: str) -> dict[str, Any] | None:
        return next((p for p in self.catalog() if p["name"] == name), None)

    def install(self, name: str) -> dict[str, Any]:
        from contentos_plugins_core.application.installer import PluginInstaller

        item = self.get(name)
        if not item:
            raise ValueError(f"Plugin '{name}' not found in marketplace")
        if item.get("builtin"):
            self._repo.set_installed(name, enabled=True, version=item["version"], source="builtin")
            return self.get(name) or item

        PluginInstaller().install_from_marketplace(name)
        self._repo.set_installed(name, enabled=False, version=item["version"], source="marketplace")
        result = self.get(name)
        if not result:
            raise ValueError(f"Install failed for '{name}'")
        return result

    def uninstall(self, name: str) -> bool:
        if name in BUILTIN_PLUGINS:
            raise ValueError(f"Cannot uninstall builtin plugin '{name}'")
        from contentos_plugins_core.application.installer import PluginInstaller

        PluginInstaller().uninstall(name)
        self._repo.remove(name)
        return True

    def set_enabled(self, name: str, enabled: bool) -> dict[str, Any]:
        item = self.get(name)
        if not item:
            raise ValueError(f"Plugin '{name}' not found")
        if not item.get("installed"):
            raise ValueError(f"Plugin '{name}' is not installed")
        self._repo.set_enabled(name, enabled)
        return self.get(name) or item

    def enabled_platforms(self) -> list[str]:
        enabled = [p["name"] for p in self.catalog() if p.get("installed") and p.get("enabled")]
        if enabled:
            return enabled
        return self._default_enabled()

    def _default_enabled(self) -> list[str]:
        raw = os.getenv("ENABLED_PLATFORMS", "tiktok,youtube,instagram")
        return [p.strip().lower() for p in raw.split(",") if p.strip()]


@lru_cache(maxsize=1)
def get_marketplace() -> PluginMarketplace:
    return PluginMarketplace()
