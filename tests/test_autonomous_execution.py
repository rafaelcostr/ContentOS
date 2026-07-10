from __future__ import annotations

from contentos_growth.application.autonomous_execution import build_autonomous_execution_plan
from contentos_growth.application.channel_manager import ChannelDailyPlan, ChannelManagerAction


def test_autonomous_execution_plan_prioritizes_ready_actions():
    channel_plan = ChannelDailyPlan(
        channel_id="channel-1",
        project_id="project-1",
        platform="youtube",
        channel_name="Canal GTA",
        summary="ok",
        health_status="healthy",
        actions=[
            ChannelManagerAction(
                action="schedule",
                title="Agendar video",
                detail="Item pronto",
                priority="high",
                calendar_item_id="cal-1",
                can_execute=True,
                execution={"type": "scheduler"},
            ),
            ChannelManagerAction(
                action="recommend",
                title="Recomendacao",
                detail="Informativa",
                priority="high",
            ),
        ],
    )

    plan = build_autonomous_execution_plan(
        project_id="project-1",
        channel_plans=[channel_plan],
        mode="assisted",
        max_actions=5,
    )
    data = plan.to_dict()

    assert data["status"] == "ready"
    assert len(data["actions"]) == 1
    assert data["actions"][0]["action"] == "schedule"
    assert data["actions"][0]["execution"]["type"] == "scheduler"


def test_autonomous_execution_plan_surfaces_blocked_actions():
    channel_plan = ChannelDailyPlan(
        channel_id="channel-1",
        project_id="project-1",
        platform="youtube",
        channel_name="Canal GTA",
        summary="ok",
        health_status="attention",
        actions=[
            ChannelManagerAction(
                action="produce",
                title="Produzir video",
                detail="Sem id",
                priority="high",
                can_execute=False,
                block_reason="Item de calendário não encontrado",
            )
        ],
    )

    plan = build_autonomous_execution_plan(
        project_id="project-1",
        channel_plans=[channel_plan],
        mode="automatic",
    )

    assert plan.status == "blocked"
    assert plan.blocked_actions[0].block_reason == "Item de calendário não encontrado"


def test_autonomous_execution_plan_limits_actions_by_priority():
    channel_plan = ChannelDailyPlan(
        channel_id="channel-1",
        project_id="project-1",
        platform="youtube",
        channel_name="Canal GTA",
        summary="ok",
        health_status="healthy",
        actions=[
            ChannelManagerAction(action="schedule", title="Baixa", detail="", priority="low", can_execute=True),
            ChannelManagerAction(action="produce", title="Alta", detail="", priority="high", can_execute=True),
        ],
    )

    plan = build_autonomous_execution_plan(
        project_id="project-1",
        channel_plans=[channel_plan],
        max_actions=1,
    )

    assert len(plan.actions) == 1
    assert plan.actions[0].title == "Alta"
