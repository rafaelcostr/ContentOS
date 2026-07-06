"""Platform publish plugins + marketplace API."""

import os

from contentos_database.models import User
from contentos_gateway.api.deps import get_current_user, require_platform_admin
from contentos_shared.plugins.loader import (
    ensure_plugins_loaded,
    get_enabled_platforms,
    list_publish_plugins,
    reload_plugins,
)
from contentos_shared.plugins.publish_base import PublishPlugin
from contentos_shared.plugins.registry import PluginRegistry
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

try:
    from contentos_plugins_core import get_marketplace
except ImportError:

    def get_marketplace():  # type: ignore[misc]
        raise HTTPException(status_code=503, detail="Plugin marketplace not available")


router = APIRouter(prefix="/plugins", tags=["Plugins"])


class PluginInfoResponse(BaseModel):
    name: str
    version: str
    description: str
    platform: str
    hooks: list[str]
    enabled: bool
    installed: bool = True
    source: str = "builtin"


class PluginsConfigResponse(BaseModel):
    publish_mode: str
    enabled_platforms: list[str]
    plugins: list[PluginInfoResponse]


class MarketplaceItemResponse(BaseModel):
    name: str
    version: str
    description: str
    platform: str
    hooks: list[str]
    builtin: bool
    installed: bool
    enabled: bool
    source: str
    category: str
    author: str


class InstallPluginRequest(BaseModel):
    name: str


class EnablePluginRequest(BaseModel):
    enabled: bool = True


@router.get("", response_model=PluginsConfigResponse)
async def list_plugins(_user: User = Depends(get_current_user)) -> PluginsConfigResponse:
    ensure_plugins_loaded()
    enabled = set(get_enabled_platforms())
    market = {p["name"]: p for p in get_marketplace().catalog()}
    plugins: list[PluginInfoResponse] = []

    for plugin in list_publish_plugins():
        meta = plugin.meta
        m = market.get(meta.name, {})
        plugins.append(
            PluginInfoResponse(
                name=meta.name,
                version=meta.version,
                description=meta.description,
                platform=plugin.platform,
                hooks=meta.hooks,
                enabled=meta.name in enabled,
                installed=m.get("installed", True),
                source=m.get("source", "builtin"),
            )
        )

    return PluginsConfigResponse(
        publish_mode=os.getenv("PUBLISH_MODE", "dry_run"),
        enabled_platforms=list(enabled),
        plugins=plugins,
    )


@router.get("/marketplace", response_model=list[MarketplaceItemResponse])
async def marketplace_catalog(_user: User = Depends(get_current_user)) -> list[MarketplaceItemResponse]:
    return [MarketplaceItemResponse(**item) for item in get_marketplace().catalog()]


@router.post("/install", response_model=MarketplaceItemResponse)
async def install_plugin(body: InstallPluginRequest, _user: User = Depends(require_platform_admin())) -> MarketplaceItemResponse:
    try:
        item = get_marketplace().install(body.name)
        reload_plugins()
        return MarketplaceItemResponse(**item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{name}")
async def uninstall_plugin(name: str, _user: User = Depends(require_platform_admin())) -> dict:
    try:
        get_marketplace().uninstall(name)
        reload_plugins()
        return {"ok": True, "name": name}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{name}/enable", response_model=MarketplaceItemResponse)
async def enable_plugin(
    name: str,
    body: EnablePluginRequest,
    _user: User = Depends(require_platform_admin()),
) -> MarketplaceItemResponse:
    try:
        item = get_marketplace().set_enabled(name, body.enabled)
        reload_plugins()
        return MarketplaceItemResponse(**item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{name}")
async def get_plugin(name: str, _user: User = Depends(get_current_user)) -> PluginInfoResponse:
    ensure_plugins_loaded()
    plugin = PluginRegistry.instance().get(name)
    if not isinstance(plugin, PublishPlugin):
        market_item = get_marketplace().get(name)
        if not market_item:
            raise HTTPException(status_code=404, detail="Plugin not found")
        return PluginInfoResponse(
            name=market_item["name"],
            version=market_item["version"],
            description=market_item["description"],
            platform=market_item.get("platform", name),
            hooks=market_item.get("hooks", []),
            enabled=market_item.get("enabled", False),
            installed=market_item.get("installed", False),
            source=market_item.get("source", "marketplace"),
        )
    meta = plugin.meta
    market_item = get_marketplace().get(name) or {}
    return PluginInfoResponse(
        name=meta.name,
        version=meta.version,
        description=meta.description,
        platform=plugin.platform,
        hooks=meta.hooks,
        enabled=name in get_enabled_platforms(),
        installed=market_item.get("installed", True),
        source=market_item.get("source", "builtin"),
    )
