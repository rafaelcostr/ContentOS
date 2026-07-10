from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from contentos_growth.application.autopilot import build_growth_autopilot_status
from contentos_growth.application.channel_manager import ChannelManagerSignals, build_channel_daily_plan
from contentos_growth.domain import ChannelProfile, GrowthRecommendation, GrowthStrategy


def _future_calendar_item(project_id: str, channel_id: str) -> dict:
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "channel_id": channel_id,
        "title": "Short do dia",
        "topic": "Como crescer no nicho",
        "status": "planned",
        "planned_for": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "metadata": {"platform": "youtube", "content_type": "short"},
    }


def test_autopilot_status_blocks_empty_project():
    project_id = str(uuid4())

    report = build_growth_autopilot_status(
        project_id=project_id,
        channels=[],
        calendar_items=[],
        recommendations=[],
        strategy=None,
        channel_plans={},
        readiness={"status": "blocked"},
    )

    data = report.to_dict()
    assert data["status"] == "blocked"
    assert data["score"] < 40
    assert any("Conecte" in blocker for blocker in data["blockers"])


def test_autopilot_status_detects_executable_daily_actions():
    project_id = str(uuid4())
    channel_id = str(uuid4())
    calendar = [_future_calendar_item(project_id, channel_id)]
    channel = ChannelProfile(
        channel_id=channel_id,
        project_id=project_id,
        platform="youtube",
        name="Canal Teste",
        score=82.0,
        has_credentials=True,
    )
    signals = ChannelManagerSignals(
        channel_id=channel_id,
        project_id=project_id,
        platform="youtube",
        channel_name="Canal Teste",
        channel_score=82.0,
        has_credentials=True,
        calendar_items=calendar,
        channel_memory={"top_hooks": ["Ninguém percebeu isso"]},
        posting_gap_days=2.0,
    )
    plan = build_channel_daily_plan(signals, scheduling_mode="automatic")

    report = build_growth_autopilot_status(
        project_id=project_id,
        channels=[channel],
        calendar_items=calendar,
        recommendations=[
            GrowthRecommendation(
                id=None,
                project_id=project_id,
                channel_id=channel_id,
                kind="hook",
                title="Reforçar hook",
                detail="Use o melhor padrão de abertura.",
            )
        ],
        strategy=GrowthStrategy(project_id=project_id, positioning="Autoridade no nicho"),
        channel_plans={channel_id: plan},
        readiness={"status": "manual_required"},
        mode="automatic",
    )

    data = report.to_dict()
    assert data["status"] in {"partial", "ready"}
    assert data["score"] >= 70
    assert data["channels"][0]["executable_actions"] >= 1
    assert any(stage["key"] == "daily_decision" and stage["status"] == "ready" for stage in data["stages"])
