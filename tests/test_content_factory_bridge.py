"""Tests for Growth → Content Factory bridge (Fase 10)."""

from __future__ import annotations

from uuid import uuid4

from contentos_growth.application.content_factory_bridge import (
    build_growth_context_json,
    prepare_calendar_dispatch,
)
from contentos_growth.domain import GrowthStrategy


def test_build_growth_context_json_includes_contract_fields():
    item_id = str(uuid4())
    channel_id = str(uuid4())
    strategy = GrowthStrategy(
        project_id=str(uuid4()),
        positioning="Autoridade em tech",
        goals=["Aumentar retenção"],
        kpis={"tone": "direto"},
        cadence={"posting_hours": [18, 20]},
        id=str(uuid4()),
    )
    calendar_item = {
        "id": item_id,
        "project_id": strategy.project_id,
        "channel_id": channel_id,
        "title": "5 hacks de produtividade",
        "topic": "produtividade remota",
        "planned_for": "2026-07-15T18:00:00+00:00",
        "status": "planned",
        "metadata": {
            "platform": "youtube",
            "content_type": "short",
            "campaign": "Q3 Growth",
        },
    }

    context = build_growth_context_json(calendar_item=calendar_item, strategy=strategy)

    assert context["topic"] == "produtividade remota"
    assert context["objective"] == "Autoridade em tech"
    assert context["target_platform"] == "youtube"
    assert context["channel_id"] == channel_id
    assert context["brand_context_ref"] == "project_memory"
    assert context["growth_plan_id"] == item_id
    assert context["growth_strategy_id"] == strategy.id
    assert context["growth_source"] == "growth_calendar"
    assert context["content_type"] == "short"
    assert context["campaign"] == "Q3 Growth"
    assert context["duration_target_seconds"] == 45
    assert context["suggested_posting_hours"] == [18, 20]


def test_prepare_calendar_dispatch_workflow_request():
    project_id = str(uuid4())
    calendar_item = {
        "id": str(uuid4()),
        "project_id": project_id,
        "title": "Título fallback",
        "topic": "",
        "status": "planned",
        "metadata": {"platform": "tiktok", "content_type": "reel"},
    }

    dispatch = prepare_calendar_dispatch(calendar_item=calendar_item, workflow_name="default")

    assert dispatch.project_id == project_id
    assert dispatch.topic == "Título fallback"
    assert dispatch.workflow_name == "default"
    request = dispatch.to_workflow_request()
    assert request["project_id"] == project_id
    assert request["auto_start"] is True
    assert request["context_json"]["target_platform"] == "tiktok"
    assert request["context_json"]["duration_target_seconds"] == 45


def test_build_growth_context_json_omits_empty_values():
    calendar_item = {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "title": "Só título",
        "topic": "",
        "status": "planned",
        "metadata": {},
    }

    context = build_growth_context_json(calendar_item=calendar_item, strategy=None)

    assert context["topic"] == "Só título"
    assert context["objective"] == "Só título"
    assert "channel_id" not in context
    assert context["target_platform"] == "youtube"
