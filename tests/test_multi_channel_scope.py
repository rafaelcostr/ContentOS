"""Multi-channel scope tests — Growth OS Fase 16."""

from __future__ import annotations

from uuid import uuid4

from contentos_growth.application.multi_channel_scope import (
    build_channel_overview_item,
    filter_calendar_by_channel,
    filter_learning_for_platform,
    filter_recommendations_for_channel,
    infer_channel_health,
    item_channel_id,
)
from contentos_growth.domain import ChannelProfile, GrowthRecommendation


def test_item_channel_id_from_metadata():
    channel_id = str(uuid4())
    item = {"metadata": {"channel_id": channel_id}}
    assert item_channel_id(item) == channel_id


def test_filter_calendar_by_channel():
    channel_a = str(uuid4())
    channel_b = str(uuid4())
    items = [
        {"id": "1", "channel_id": channel_a, "status": "planned"},
        {"id": "2", "channel_id": channel_b, "status": "planned"},
        {"id": "3", "metadata": {"channel_id": channel_a}, "status": "planned"},
    ]
    filtered = filter_calendar_by_channel(items, channel_a)
    assert len(filtered) == 2


def test_filter_recommendations_for_channel():
    channel_id = str(uuid4())
    recs = [
        GrowthRecommendation(
            id=None,
            project_id=str(uuid4()),
            channel_id=channel_id,
            kind="hook",
            title="Canal",
            detail="",
        ),
        GrowthRecommendation(
            id=None,
            project_id=str(uuid4()),
            channel_id=None,
            kind="strategy",
            title="Projeto",
            detail="",
        ),
        GrowthRecommendation(
            id=None,
            project_id=str(uuid4()),
            channel_id=str(uuid4()),
            kind="other",
            title="Outro canal",
            detail="",
        ),
    ]
    scoped = filter_recommendations_for_channel(recs, channel_id)
    assert len(scoped) == 2
    titles = {rec.title for rec in scoped}
    assert "Canal" in titles
    assert "Projeto" in titles


def test_filter_learning_for_platform():
    rows = [
        {"platform": "youtube", "insight": "a"},
        {"platform": "tiktok", "insight": "b"},
        {"insight": "generic"},
    ]
    filtered = filter_learning_for_platform(rows, "youtube")
    assert len(filtered) == 2


def test_infer_channel_health_critical_without_credentials():
    profile = ChannelProfile(
        channel_id=str(uuid4()),
        project_id=str(uuid4()),
        platform="youtube",
        name="Test",
        score=80,
        has_credentials=False,
    )
    assert infer_channel_health(profile=profile, calendar=[], performance=[]) == "critical"


def test_build_channel_overview_item_counts():
    channel_id = str(uuid4())
    profile = ChannelProfile(
        channel_id=channel_id,
        project_id=str(uuid4()),
        platform="youtube",
        name="Canal A",
        score=75,
        has_credentials=True,
    )
    calendar = [
        {"channel_id": channel_id, "status": "planned"},
        {"channel_id": channel_id, "status": "scheduled"},
    ]
    recs = [
        GrowthRecommendation(
            id=None,
            project_id=profile.project_id,
            channel_id=channel_id,
            kind="hook",
            title="A",
            detail="",
            status="open",
        )
    ]
    overview = build_channel_overview_item(
        profile,
        calendar=calendar,
        recommendations=recs,
        performance=[],
    )
    assert overview.calendar_planned == 1
    assert overview.calendar_scheduled == 1
    assert overview.recommendations_open == 1
    assert overview.health_status in ("healthy", "attention")
