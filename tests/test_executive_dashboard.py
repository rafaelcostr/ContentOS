"""Tests for Executive Dashboard (V4.3.2 / Epic 12)."""

from __future__ import annotations

from contentos_intelligence.application.executive.command_center import build_command_center_alerts
from contentos_intelligence.application.executive.summary_service import _module_status
from contentos_intelligence.application.specialists.catalog import list_specialists
from contentos_intelligence.domain.executive_summary import ExecutiveSummary, ModuleStatus


def test_module_status_to_dict():
    mod = _module_status("viral", "Viral", "72", "/viral", detail="avg", active=True)
    d = mod.to_dict()
    assert d["key"] == "viral"
    assert d["status"] == "active"
    assert d["href"] == "/viral"


def test_executive_summary_to_dict():
    summary = ExecutiveSummary(
        project_id="p1",
        project_name="Demo",
        knowledge_entries=10,
        modules=[ModuleStatus("kb", "KB", "active", "10", "/knowledge")],
    )
    d = summary.to_dict()
    assert d["project_name"] == "Demo"
    assert d["knowledge_entries"] == 10
    assert len(d["modules"]) == 1


def test_specialists_available_for_executive():
    specialists = list_specialists(include_upcoming=False)
    assert len(specialists) >= 3


def test_executive_module_keys():
    keys = {
        _module_status("viral", "Viral", "—", "/viral").key,
        _module_status("graph", "Graph", "0", "/content-graph").key,
    }
    assert "viral" in keys
    assert "graph" in keys


def test_command_center_alerts_factory_pending():
    alerts = build_command_center_alerts(
        factory_pending_approval=2,
        community_drafts_pending=0,
        oauth_channels_connected=1,
        platform_snapshots=5,
    )
    assert any("aprovação" in a for a in alerts)


def test_executive_summary_v5_fields():
    summary = ExecutiveSummary(
        project_id="p1",
        project_name="Demo",
        factory_batches_total=3,
        v5_modules=[ModuleStatus("factory", "Factory", "active", "3", "/factory")],
        alerts=["test alert"],
        slo_items=[{"id": "redis-availability", "state": "ok"}],
    )
    d = summary.to_dict()
    assert d["factory_batches_total"] == 3
    assert len(d["v5_modules"]) == 1
    assert d["alerts"] == ["test alert"]
    assert len(d["slo_items"]) == 1
