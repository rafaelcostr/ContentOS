"""Discover marketplace and installed plugin manifests."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from contentos_plugins_core.domain.plugin_manifest import PluginManifest


def plugins_root() -> Path:
    env = os.getenv("PLUGINS_ROOT", "")
    if env:
        return Path(env)
    # repo root: packages/plugins-core -> ../../plugins
    here = Path(__file__).resolve()
    candidate = here.parents[5] / "plugins"
    if candidate.is_dir():
        return candidate
    return Path("/app/plugins")


def marketplace_dir() -> Path:
    return plugins_root() / "marketplace"


def installed_dir() -> Path:
    return plugins_root() / "installed"


def load_yaml_manifest(path: Path) -> PluginManifest | None:
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return PluginManifest.from_dict(data)
    except Exception:
        return None
    return None


def discover_marketplace() -> list[PluginManifest]:
    root = marketplace_dir()
    if not root.is_dir():
        return []
    manifests: list[PluginManifest] = []
    seen: set[str] = set()
    for path in sorted(root.glob("*.yaml")):
        m = load_yaml_manifest(path)
        if m and m.name not in seen:
            manifests.append(m)
            seen.add(m.name)
    for child in sorted(root.iterdir()):
        if child.is_dir():
            m = load_yaml_manifest(child / "plugin.yaml")
            if m and m.name not in seen:
                manifests.append(m)
                seen.add(m.name)
    return manifests


def discover_installed() -> list[PluginManifest]:
    root = installed_dir()
    if not root.is_dir():
        return []
    manifests: list[PluginManifest] = []
    for child in sorted(root.iterdir()):
        if child.is_dir():
            m = load_yaml_manifest(child / "plugin.yaml")
            if m:
                manifests.append(m)
    return manifests


def installed_plugin_path(name: str) -> Path | None:
    path = installed_dir() / name
    if path.is_dir() and (path / "plugin.yaml").is_file():
        return path
    return None
