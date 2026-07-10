from __future__ import annotations

from contentos_growth.application.autonomous_execution import (
    AutonomousExecutionAction,
    AutonomousExecutionPlan,
)
from contentos_growth.application.closed_loop import build_closed_loop_report
from contentos_growth.application.performance_learning_interpreter import interpret_performance_insights
from contentos_growth.domain import GrowthReport


def test_closed_loop_blocks_without_performance():
    performance = interpret_performance_insights("project-1", [])
    growth_report = GrowthReport(
        project_id="project-1",
        summary="report",
        score=45,
        risks=["Sem snapshots de analytics OAuth"],
    )

    report = build_closed_loop_report(
        project_id="project-1",
        growth_report=growth_report,
        performance=performance,
    )

    assert report.status == "blocked"
    assert report.blockers
    assert report.next_cycle["sync_performance"] is True


def test_closed_loop_recommends_memory_and_calendar_updates():
    performance = interpret_performance_insights(
        "project-1",
        [
            {
                "platform": "youtube",
                "title": "Short viral",
                "views": 10000,
                "ctr": 0.08,
                "retention_pct": 70,
                "performance_tier": "high",
                "hook_text": "Voce nao viu esse detalhe",
            }
        ],
    )
    growth_report = GrowthReport(project_id="project-1", summary="report", score=72)

    report = build_closed_loop_report(
        project_id="project-1",
        growth_report=growth_report,
        performance=performance,
        saved_recommendations=2,
    )

    assert report.status == "ready"
    assert report.memory_updates
    assert report.calendar_updates
    assert any("recomendacao" in item.lower() for item in report.learned)


def test_closed_loop_includes_execution_plan():
    performance = interpret_performance_insights(
        "project-1",
        [{"platform": "youtube", "views": 1000, "ctr": 0.04, "performance_tier": "medium"}],
    )
    growth_report = GrowthReport(project_id="project-1", summary="report", score=65)
    execution_plan = AutonomousExecutionPlan(
        project_id="project-1",
        mode="assisted",
        status="ready",
        summary="ok",
        actions=[
            AutonomousExecutionAction(
                channel_id="channel-1",
                project_id="project-1",
                platform="youtube",
                channel_name="Main",
                action="schedule",
                title="Agendar",
                detail="ok",
                priority="high",
                can_execute=True,
            )
        ],
    )

    report = build_closed_loop_report(
        project_id="project-1",
        growth_report=growth_report,
        performance=performance,
        execution_plan=execution_plan,
    )

    assert report.next_cycle["run_autopilot"] is True
    assert report.execution_updates
