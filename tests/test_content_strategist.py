"""Tests for Content Strategist — Growth OS Fase 9."""

from __future__ import annotations

from uuid import uuid4

from contentos_growth.application.content_strategist import generate_content_strategy_plan
from contentos_growth.domain import ChannelProfile, GrowthRecommendation, GrowthStrategy


def test_generate_content_strategy_plan_creates_calendar():
    project_id = str(uuid4())
    channels = [
        ChannelProfile(
            channel_id=str(uuid4()),
            project_id=project_id,
            platform="youtube",
            name="Main",
            score=75,
            has_credentials=True,
            analyzed_at="2026-07-09",
            profile={"shorts_ratio": 0.2, "posting_gap_days": 5},
        )
    ]
    recommendations = [
        GrowthRecommendation(
            id=None,
            project_id=project_id,
            channel_id=None,
            kind="content",
            title="Testar hook de pergunta",
            detail="CTR alto em formato similar",
            source="performance_learning",
        )
    ]
    plan = generate_content_strategy_plan(
        project_id=project_id,
        channels=channels,
        recommendations=recommendations,
        positioning="Educar sobre finanças",
        opportunities=["Replicar formato de alto desempenho"],
        channel_memory_by_channel={
            channels[0].channel_id: {"top_hooks": ["3 erros fatais"], "best_posting_hours": [18, 20]}
        },
        horizon_days=14,
    )
    assert plan.strategy.positioning == "Educar sobre finanças"
    assert plan.calendar.items
    assert plan.campaigns
    assert channels[0].channel_id in plan.channel_goals
    assert plan.strategy.cadence["weekly_posts"] >= 2
    assert 18 in plan.strategy.cadence["posting_hours"]


def test_generate_plan_without_channels_uses_defaults():
    plan = generate_content_strategy_plan(
        project_id=str(uuid4()),
        channels=[],
        recommendations=[],
        positioning="Nicho tech",
        horizon_days=7,
    )
    assert plan.calendar.items
    assert plan.summary
