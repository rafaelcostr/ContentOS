"""Channel Manager AI tests — Growth OS Fase 15."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from contentos_growth.application.channel_manager import (
    ChannelManagerSignals,
    build_channel_daily_plan,
    enrich_channel_manager_actions,
    filter_calendar_for_channel,
    filter_performance_for_platform,
)
from contentos_growth.domain import GrowthStrategy


def _future_item(**overrides) -> dict:
    planned = datetime.now(timezone.utc) + timedelta(days=2)
    base = {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "channel_id": str(uuid4()),
        "title": "Short viral",
        "topic": "5 dicas de produtividade",
        "planned_for": planned.isoformat(),
        "status": "planned",
        "metadata": {"platform": "youtube", "content_type": "short"},
    }
    base.update(overrides)
    return base


def _signals(**overrides) -> ChannelManagerSignals:
    channel_id = str(uuid4())
    base = ChannelManagerSignals(
        channel_id=channel_id,
        project_id=str(uuid4()),
        platform="youtube",
        channel_name="Canal Teste",
        channel_score=72.0,
        has_credentials=True,
        channel_memory={"top_hooks": ["Você não vai acreditar"]},
        performance_rows=[
            {"platform": "youtube", "performance_tier": "high", "title": "Vídeo top", "topic": "produtividade"},
            {"platform": "tiktok", "performance_tier": "low", "title": "Outro"},
        ],
        calendar_items=[_future_item(channel_id=channel_id)],
        posting_gap_days=3.0,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_filter_performance_for_platform():
    rows = [
        {"platform": "youtube", "title": "A"},
        {"platform": "tiktok", "title": "B"},
    ]
    filtered = filter_performance_for_platform(rows, "youtube")
    assert len(filtered) == 1
    assert filtered[0]["title"] == "A"


def test_filter_calendar_for_channel():
    channel_id = str(uuid4())
    items = [
        _future_item(channel_id=channel_id),
        _future_item(channel_id=str(uuid4())),
    ]
    assert len(filter_calendar_for_channel(items, channel_id)) == 1


def test_build_plan_schedules_video_in_assisted_mode():
    signals = _signals()
    plan = build_channel_daily_plan(signals, scheduling_mode="assisted")
    assert plan.health_status in ("healthy", "attention")
    assert any(action.action == "schedule" for action in plan.actions)
    assert plan.focus_topics


def test_build_plan_produces_video_in_automatic_mode():
    signals = _signals()
    plan = build_channel_daily_plan(signals, scheduling_mode="automatic")
    assert any(action.action == "produce" for action in plan.actions)


def test_build_plan_text_post_action():
    channel_id = str(uuid4())
    item = _future_item(
        channel_id=channel_id,
        metadata={"platform": "linkedin", "content_type": "post"},
    )
    signals = _signals(channel_id=channel_id, calendar_items=[item], platform="linkedin")
    plan = build_channel_daily_plan(signals)
    assert any(action.action == "generate_post" for action in plan.actions)


def test_build_plan_critical_without_credentials():
    signals = _signals(has_credentials=False, channel_score=30.0)
    plan = build_channel_daily_plan(signals)
    assert plan.health_status == "critical"
    assert any("OAuth" in risk for risk in plan.risks)


def test_build_plan_recommends_when_no_calendar():
    signals = _signals(calendar_items=[], posting_gap_days=10.0)
    plan = build_channel_daily_plan(signals)
    assert any(action.action == "recommend" for action in plan.actions)


def test_enrich_attaches_workflow_payload():
    channel_id = str(uuid4())
    item = _future_item(channel_id=channel_id)
    signals = _signals(channel_id=channel_id, calendar_items=[item])
    plan = build_channel_daily_plan(signals, scheduling_mode="automatic")
    enriched = enrich_channel_manager_actions(
        plan,
        calendar_by_id={item["id"]: item},
        strategy=GrowthStrategy(project_id=signals.project_id, positioning="Autoridade"),
        scheduling_mode="automatic",
    )
    produce_actions = [a for a in enriched.actions if a.action == "produce"]
    assert produce_actions
    assert produce_actions[0].execution.get("type") == "workflow"
    assert produce_actions[0].execution["workflow_request"]["topic"]
