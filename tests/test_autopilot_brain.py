from __future__ import annotations

from contentos_autopilot import AutopilotAction, AutopilotBrain, AutopilotContext, AutopilotSignal


def test_autopilot_brain_returns_decision_without_execution():
    context = AutopilotContext(
        project_id="project-1",
        mode="assisted",
        score=80,
        summary="ok",
        signals=[
            AutopilotSignal(
                source="growth",
                kind="status",
                title="Growth pronto",
            )
        ],
        candidate_actions=[
            AutopilotAction(
                action="schedule",
                title="Agendar proximo video",
                detail="Item pronto para delegar",
                priority="high",
                delegate_to="scheduler",
                can_delegate=True,
            ),
            AutopilotAction(
                action="publish",
                title="Publicar direto",
                detail="Bloqueado sem autorizacao",
                priority="high",
                delegate_to="publisher",
                can_delegate=False,
                block_reason="Publicacao exige autorizacao",
            ),
        ],
    )

    decision = AutopilotBrain().decide(context)
    data = decision.to_dict()

    assert data["status"] == "ready"
    assert len(data["actions"]) == 1
    assert data["actions"][0]["delegate_to"] == "scheduler"
    assert data["signals"][0]["source"] == "growth"


def test_autopilot_brain_blocks_when_only_blockers_exist():
    context = AutopilotContext(
        project_id="project-1",
        score=30,
        blockers=["OAuth pendente"],
        candidate_actions=[],
    )

    decision = AutopilotBrain().decide(context)

    assert decision.status == "blocked"
    assert decision.blockers == ["OAuth pendente"]


def test_autopilot_brain_limits_actions_by_priority():
    context = AutopilotContext(
        project_id="project-1",
        score=90,
        candidate_actions=[
            AutopilotAction(action="low", title="B", detail="", priority="low", can_delegate=True),
            AutopilotAction(action="high", title="A", detail="", priority="high", can_delegate=True),
        ],
    )

    decision = AutopilotBrain().decide(context, max_actions=1)

    assert len(decision.actions) == 1
    assert decision.actions[0].action == "high"
