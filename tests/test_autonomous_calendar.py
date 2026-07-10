from __future__ import annotations

from datetime import datetime, timezone

from contentos_growth.application.autonomous_calendar import build_autonomous_calendar_plan
from contentos_growth.application.channel_intelligence import build_channel_intelligence_snapshot
from contentos_growth.domain import ChannelProfile, GrowthStrategy


def _snapshot():
    return build_channel_intelligence_snapshot(
        channel=ChannelProfile(
            channel_id="channel-1",
            project_id="project-1",
            platform="youtube",
            name="Canal GTA",
            score=82,
            has_credentials=True,
            profile={"niche": "GTA 6"},
        ),
        channel_memory={
            "top_themes": ["segredos do GTA 6", "mapa do GTA 6"],
            "top_hooks": ["A Rockstar escondeu isso"],
            "best_posting_hours": [18, 21],
        },
        strategy=GrowthStrategy(project_id="project-1", cadence={"weekly_posts": 3, "posting_hours": [20]}),
    )


def test_autonomous_calendar_proposes_missing_slots():
    plan = build_autonomous_calendar_plan(
        project_id="project-1",
        snapshots=[_snapshot()],
        existing_calendar=[],
        strategy=GrowthStrategy(project_id="project-1", cadence={"weekly_posts": 3}),
        horizon_days=14,
        max_items=5,
        mode="draft",
    )

    data = plan.to_dict()

    assert data["status"] == "ready"
    assert data["proposed_items"]
    assert data["calendar_items"][0]["status"] == "planned"
    assert data["calendar_items"][0]["metadata"]["source"] == "autonomous_calendar"
    assert data["calendar_items"][0]["metadata"]["platform"] == "youtube"
    assert data["calendar_items"][0]["metadata"]["objective_status"] == "linked"
    assert data["calendar_items"][0]["metadata"]["objective_path"]


def test_autonomous_calendar_preserves_existing_topics():
    plan = build_autonomous_calendar_plan(
        project_id="project-1",
        snapshots=[_snapshot()],
        existing_calendar=[
            {
                "title": "segredos do GTA 6",
                "topic": "segredos do GTA 6",
                "planned_for": datetime.now(timezone.utc).isoformat(),
                "status": "planned",
            }
        ],
        strategy=GrowthStrategy(project_id="project-1", cadence={"weekly_posts": 3}),
        horizon_days=7,
        max_items=3,
    )

    topics = [item.topic for item in plan.proposed_items]

    assert "segredos do GTA 6" not in topics


def test_autonomous_calendar_blocks_without_channels():
    plan = build_autonomous_calendar_plan(
        project_id="project-1",
        snapshots=[],
        existing_calendar=[],
    )

    assert plan.status == "blocked"
    assert plan.gaps
