"""V5.2.4 — AI Director tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_events.domain.event_types import DIRECTOR_DECIDED, STEP_TO_DOMAIN_EVENT
from contentos_intelligence.application.director import plan_director_decision, resolve_director_retry_from
from contentos_shared.enums import PipelineStep


def test_plan_director_passes_when_scores_ok():
    decision = plan_director_decision(
        {
            "content_score": 78,
            "content_score_report": {
                "total_score": 78,
                "dimensions": [
                    {"name": "hook", "score": 80, "weight": 0.15},
                    {"name": "retention", "score": 75, "weight": 0.15},
                    {"name": "seo", "score": 70, "weight": 0.1},
                ],
            },
        }
    )
    assert decision.passed is True
    assert decision.action == "advance"
    assert decision.retry_from == ""


def test_plan_director_retries_weakest_dimension():
    decision = plan_director_decision(
        {
            "content_score": 52,
            "content_score_report": {
                "total_score": 52,
                "dimensions": [
                    {"name": "hook", "score": 72, "weight": 0.15},
                    {"name": "retention", "score": 40, "weight": 0.15},
                    {"name": "cta", "score": 50, "weight": 0.1},
                ],
            },
            "retention_report": {
                "overall_score": 40,
                "hook_retention_pct": 80,
                "completion_pct": 50,
                "weak_segments": [],
                "drop_seconds": [],
            },
        }
    )
    assert decision.passed is False
    assert decision.action == "retry"
    assert decision.retry_from in ("takes", "hook", "script")


def test_plan_director_maps_technical_to_editor():
    decision = plan_director_decision(
        {
            "content_score": 60,
            "quality_score": 4,
            "content_score_report": {
                "total_score": 60,
                "dimensions": [
                    {"name": "hook", "score": 70, "weight": 0.15},
                    {"name": "technical", "score": 35, "weight": 0.1},
                ],
            },
        }
    )
    assert decision.passed is False
    assert decision.target == "edit"
    assert decision.retry_from == "editor"


def test_resolve_director_retry_from_fallback():
    steps = ["research", "script", "takes", "editor", "quality"]
    assert resolve_director_retry_from("scene_director", steps) == "script"


def test_factory_full_includes_ai_director():
    steps = PipelineStep.factory_full_ordered()
    assert len(steps) == 31
    assert steps.index(PipelineStep.CONTENT_SCORE) + 1 == steps.index(PipelineStep.AI_DIRECTOR)
    assert steps.index(PipelineStep.AI_DIRECTOR) + 1 == steps.index(PipelineStep.CONTENT_INTELLIGENCE)


def test_v5_autopilot_includes_ai_director():
    steps = PipelineStep.v5_media_autopilot_ordered()
    assert len(steps) == 18
    assert steps.index(PipelineStep.QUALITY) + 1 == steps.index(PipelineStep.RETENTION)
    assert steps.index(PipelineStep.RETENTION) + 1 == steps.index(PipelineStep.AI_DIRECTOR)
    assert steps.index(PipelineStep.AI_DIRECTOR) + 1 == steps.index(PipelineStep.SEO)


def test_director_domain_event():
    assert STEP_TO_DOMAIN_EVENT["ai_director"] == DIRECTOR_DECIDED


@pytest.mark.asyncio
async def test_ai_director_agent_handler():
    from contentos_agents.handlers.ai_director import AiDirectorAgentHandler
    from contentos_shared.schemas.agent import AgentTaskInput

    handler = AiDirectorAgentHandler()

    async def fake_store(_self, category, data, meta):
        return type("R", (), {"key": "scripts/director.json", "bucket": "contentos", "id": uuid4()})()

    handler.get_asset_manager = lambda: type("M", (), {"store": fake_store})()

    output = await handler.execute(
        AgentTaskInput(
            job_id=uuid4(),
            project_id=uuid4(),
            pipeline_id=uuid4(),
            step="ai_director",
            payload={
                "topic": "GTA 6",
                "content_score": 50,
                "content_score_report": {
                    "total_score": 50,
                    "dimensions": [{"name": "retention", "score": 42, "weight": 0.15}],
                },
            },
        )
    )
    assert output.data["director_passed"] is False
    assert output.data["director_action"] == "retry"
    assert output.data["creative_retry_from"]
