"""Dynamic plugin loader from installed directory."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from contentos_plugins_core.domain.plugin_manifest import PluginManifest
from contentos_plugins_core.infrastructure.discovery import installed_plugin_path, load_yaml_manifest
from contentos_shared.plugins.registry import ContentOSPlugin


def load_plugin_instance(manifest: PluginManifest, install_path: Path | None = None) -> ContentOSPlugin | None:
    if manifest.builtin or not manifest.entrypoint:
        return None
    path = install_path or installed_plugin_path(manifest.name)
    if not path:
        return None
    manifest = load_yaml_manifest(path / "plugin.yaml") or manifest
    module_file, class_name = _parse_entrypoint(manifest.entrypoint)
    module_path = path / f"{module_file}.py"
    if not module_path.is_file():
        return None

    module_key = f"contentos_plugin_{manifest.name}"
    if module_key in sys.modules:
        module = sys.modules[module_key]
    else:
        spec = importlib.util.spec_from_file_location(module_key, module_path)
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_key] = module
        spec.loader.exec_module(module)

    plugin_cls = getattr(module, class_name, None)
    if plugin_cls is None:
        return None
    return plugin_cls()


def _parse_entrypoint(entrypoint: str) -> tuple[str, str]:
    if "." not in entrypoint:
        return entrypoint, entrypoint
    module_file, class_name = entrypoint.rsplit(".", 1)
    return module_file, class_name
