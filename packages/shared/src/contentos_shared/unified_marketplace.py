"""Unified marketplace catalog — plugins, agents, workflows (V3 Tier D3)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from contentos_shared.agent_catalog import AGENT_CATALOG
from contentos_shared.workflow_templates import BUILTIN_TEMPLATES

_remote_cache: dict[str, Any] = {"items": [], "fetched_at": 0.0}


def marketplace_remote_url() -> str | None:
    url = os.getenv("MARKETPLACE_REMOTE_URL", "").strip()
    return url or None


def marketplace_cache_ttl() -> int:
    try:
        return max(60, int(os.getenv("MARKETPLACE_REMOTE_CACHE_SECONDS", "300")))
    except ValueError:
        return 300


def _local_remote_catalog_path() -> Path | None:
    root = os.getenv("PLUGINS_ROOT", "plugins")
    path = Path(root) / "marketplace" / "unified_remote.json"
    return path if path.is_file() else None


def fetch_remote_items() -> list[dict[str, Any]]:
    """Load optional remote catalog (HTTP or local JSON fallback)."""
    now = time.time()
    if _remote_cache["items"] and now - _remote_cache["fetched_at"] < marketplace_cache_ttl():
        return list(_remote_cache["items"])

    items: list[dict[str, Any]] = []
    url = marketplace_remote_url()
    if url:
        try:
            import httpx

            resp = httpx.get(url, timeout=10.0)
            if resp.status_code == 200:
                payload = resp.json()
                items = list(payload.get("items") or [])
        except Exception:
            items = []

    if not items:
        local = _local_remote_catalog_path()
        if local:
            try:
                payload = json.loads(local.read_text(encoding="utf-8"))
                items = list(payload.get("items") or [])
            except Exception:
                items = []

    _remote_cache["items"] = items
    _remote_cache["fetched_at"] = now
    return list(items)


def plugin_items() -> list[dict[str, Any]]:
    try:
        from contentos_plugins_core import get_marketplace

        catalog = get_marketplace().catalog()
    except Exception:
        catalog = []
    out: list[dict[str, Any]] = []
    for p in catalog:
        out.append(
            {
                "id": f"plugin:{p['name']}",
                "type": "plugin",
                "name": p["name"],
                "description": p.get("description", ""),
                "version": p.get("version", "1.0.0"),
                "author": p.get("author", "ContentOS"),
                "category": p.get("category", "publish"),
                "source": p.get("source", "local"),
                "installed": p.get("installed"),
                "enabled": p.get("enabled"),
                "platform": p.get("platform"),
                "hooks": p.get("hooks", []),
                "builtin": p.get("builtin", False),
            }
        )
    return out


def agent_items() -> list[dict[str, Any]]:
    return [
        {
            "id": f"agent:{a['name']}",
            "type": "agent",
            "name": a["name"],
            "description": a["description"],
            "version": "1.0.0",
            "author": "ContentOS",
            "category": a.get("category", "creative"),
            "source": "local",
            "queue": a["queue"],
            "tier": a.get("tier", "core"),
            "installed": True,
            "enabled": True,
        }
        for a in AGENT_CATALOG
    ]


def workflow_items_from_templates(extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for tpl in BUILTIN_TEMPLATES.values():
        items.append(
            {
                "id": f"workflow:{tpl['name']}",
                "type": "workflow",
                "name": tpl["name"],
                "description": tpl.get("description", ""),
                "version": "1.0.0",
                "author": "ContentOS",
                "category": "pipeline",
                "source": "builtin",
                "steps": list(tpl.get("steps") or []),
                "step_count": len(tpl.get("steps") or []),
                "is_default": tpl.get("is_default", False),
                "installed": True,
                "enabled": True,
            }
        )
    for row in extra or []:
        items.append(
            {
                "id": f"workflow:{row['name']}",
                "type": "workflow",
                "name": row["name"],
                "description": row.get("description") or "",
                "version": "1.0.0",
                "author": "Organization",
                "category": "pipeline",
                "source": "custom",
                "steps": list(row.get("steps") or []),
                "step_count": len(row.get("steps") or []),
                "slug": row.get("slug"),
                "org_id": str(row["org_id"]) if row.get("org_id") else None,
                "installed": True,
                "enabled": True,
            }
        )
    return items


def normalize_remote_item(raw: dict[str, Any]) -> dict[str, Any] | None:
    item_type = str(raw.get("type", "")).lower()
    name = str(raw.get("name", "")).strip()
    if item_type not in ("plugin", "agent", "workflow") or not name:
        return None
    return {
        "id": raw.get("id") or f"{item_type}:{name}",
        "type": item_type,
        "name": name,
        "description": str(raw.get("description", "")),
        "version": str(raw.get("version", "1.0.0")),
        "author": str(raw.get("author", "Community")),
        "category": str(raw.get("category", "community")),
        "source": "remote",
        "installed": raw.get("installed"),
        "enabled": raw.get("enabled"),
        "steps": raw.get("steps"),
        "step_count": len(raw.get("steps") or []) if raw.get("steps") else raw.get("step_count"),
        "queue": raw.get("queue"),
        "metadata": raw.get("metadata") or {},
    }


def build_unified_catalog(
    *,
    custom_workflows: list[dict[str, Any]] | None = None,
    item_type: str | None = None,
) -> list[dict[str, Any]]:
    """Merge local plugins, agents, workflows and remote catalog."""
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []

    for batch in (plugin_items(), agent_items(), workflow_items_from_templates(custom_workflows)):
        for item in batch:
            key = item["id"]
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

    for raw in fetch_remote_items():
        item = normalize_remote_item(raw)
        if not item or item["id"] in seen:
            continue
        seen.add(item["id"])
        merged.append(item)

    if item_type:
        merged = [i for i in merged if i["type"] == item_type.lower()]
    return sorted(merged, key=lambda i: (i["type"], i["name"]))


def catalog_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"plugin": 0, "agent": 0, "workflow": 0, "total": len(items)}
    for item in items:
        t = item.get("type")
        if t in summary:
            summary[t] += 1
    return summary
