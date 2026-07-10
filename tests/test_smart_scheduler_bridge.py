"""Smart Scheduler bridge tests — Growth OS Fase 13."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from contentos_growth.application.smart_scheduler_bridge import (
    build_growth_schedule_plan,
    can_schedule_calendar_item,
    normalize_scheduling_mode,
    planned_for_to_cron,
)
from contentos_growth.domain import GrowthStrategy


def _future_item(**overrides) -> dict:
    planned = datetime.now(timezone.utc) + timedelta(days=3)
    base = {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "title": "Short viral",
        "topic": "5 dicas de produtividade",
        "planned_for": planned.isoformat(),
        "status": "planned",
        "metadata": {"platform": "youtube", "content_type": "short"},
    }
    base.update(overrides)
    return base


def test_normalize_scheduling_mode():
    assert normalize_scheduling_mode("automatic") == "automatic"
    assert normalize_scheduling_mode("assistido") == "assisted"
    assert normalize_scheduling_mode("auto") == "automatic"


def test_can_schedule_rejects_text_posts():
    item = _future_item(metadata={"platform": "linkedin", "content_type": "post"})
    ok, reason = can_schedule_calendar_item(item)
    assert not ok
    assert "texto" in (reason or "").lower()


def test_can_schedule_requires_future_planned_for():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    item = _future_item(planned_for=past.isoformat())
    ok, _ = can_schedule_calendar_item(item)
    assert not ok


def test_planned_for_to_cron():
    planned = datetime(2026, 7, 15, 18, 30, tzinfo=timezone.utc)
    assert planned_for_to_cron(planned, "UTC") == "30 18 15 7 *"


def test_build_growth_schedule_plan_automatic():
    item = _future_item()
    strategy = GrowthStrategy(project_id=item["project_id"], positioning="Autoridade", goals=["Views"])
    plan = build_growth_schedule_plan(calendar_item=item, strategy=strategy, mode="automatic", timezone="UTC")
    assert plan.is_active is True
    assert plan.mode == "automatic"
    assert plan.context_json["growth_plan_id"] == item["id"]
    assert plan.context_json["growth_scheduling_mode"] == "automatic"
    assert plan.name.startswith("Growth:")


def test_build_growth_schedule_plan_assisted_inactive():
    item = _future_item()
    plan = build_growth_schedule_plan(calendar_item=item, strategy=None, mode="assisted")
    assert plan.is_active is False
    assert plan.mode == "assisted"


def test_build_growth_schedule_plan_manual_raises():
    item = _future_item()
    with pytest.raises(ValueError, match="manual"):
        build_growth_schedule_plan(calendar_item=item, strategy=None, mode="manual")
