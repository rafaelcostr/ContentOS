"""Tier D3 — unified marketplace."""

from pathlib import Path

import pytest
from contentos_shared.unified_marketplace import (
    agent_items,
    build_unified_catalog,
    catalog_summary,
    normalize_remote_item,
    workflow_items_from_templates,
)


def test_agent_items_count():
    items = agent_items()
    assert len(items) >= 18
    assert all(i["type"] == "agent" for i in items)


def test_workflow_templates_in_catalog():
    items = workflow_items_from_templates()
    names = {i["name"] for i in items}
    assert "v1-default" in names
    assert "v3-quality" in names


def test_build_unified_catalog_types():
    items = build_unified_catalog()
    types = {i["type"] for i in items}
    assert "agent" in types
    assert "workflow" in types
    summary = catalog_summary(items)
    assert summary["total"] == len(items)


def test_normalize_remote_item():
    item = normalize_remote_item(
        {"type": "workflow", "name": "remote-pack", "description": "x", "steps": ["research"]}
    )
    assert item is not None
    assert item["source"] == "remote"
    assert item["step_count"] == 1


def test_local_remote_json_fallback(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    remote = root / "plugins" / "marketplace" / "unified_remote.json"
    if not remote.is_file():
        pytest.skip("unified_remote.json not present")
    monkeypatch.delenv("MARKETPLACE_REMOTE_URL", raising=False)
    monkeypatch.setenv("PLUGINS_ROOT", str(root / "plugins"))
    from contentos_shared import unified_marketplace as um

    um._remote_cache["fetched_at"] = 0
    um._remote_cache["items"] = []
    items = build_unified_catalog()
    names = {i["name"] for i in items if i["source"] == "remote"}
    assert "community-shorts-pack" in names
