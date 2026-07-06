"""Install plugins from marketplace templates into plugins/installed/."""

from __future__ import annotations

import shutil
from pathlib import Path

from contentos_plugins_core.infrastructure.discovery import (
    installed_dir,
    installed_plugin_path,
    load_yaml_manifest,
    marketplace_dir,
)


class PluginInstaller:
    def install_from_marketplace(self, name: str) -> Path:
        src = marketplace_dir() / name
        if src.is_dir() and (src / "plugin.yaml").is_file():
            return self._copy_plugin_tree(src, name)

        manifest_path = marketplace_dir() / f"{name}.yaml"
        manifest = load_yaml_manifest(manifest_path)
        if not manifest:
            raise ValueError(f"No marketplace package for plugin '{name}'")

        template = marketplace_dir() / "_template"
        if template.is_dir():
            return self._copy_plugin_tree(template, name, manifest_name=name)

        raise ValueError(f"Cannot install plugin '{name}' — no package files in marketplace")

    def uninstall(self, name: str) -> None:
        path = installed_plugin_path(name)
        if path and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)

    def _copy_plugin_tree(self, src: Path, name: str, manifest_name: str | None = None) -> Path:
        dest = installed_dir() / name
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)
        if manifest_name and not (dest / "plugin.yaml").is_file():
            raise ValueError(f"Installed plugin '{name}' missing plugin.yaml")
        return dest
