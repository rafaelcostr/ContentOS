"""V5.2.1 — Retention Engine tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_events.domain.event_types import RETENTION_ANALYZED, STEP_TO_DOMAIN_EVENT
from contentos_intelligence.application.content_score.dimensions import extract_retention
from contentos_intelligence.application.retention import RetentionAnalyzer
from contentos_shared.enums import PipelineStep


def test_retention_analyzer_second_by_second():
    payload = {
        "duration_seconds": 20,
        "emotion": {"curiosity": 9, "retention": 8, "overall": 8},
        "scenes": [
            {"label": "hook", "start_seconds": 0, "end_seconds": 5},
            {"label": "body", "start_seconds": 5, "end_seconds": 15},
            {"label": "cta", "start_seconds": 15, "end_seconds": 20},
        ],
        "director_plan": {
            "segments": [
                {"movement": "speed-ramp-up", "transition": "cut"},
                {"movement": "static", "transition": "fade"},
                {"movement": "zoom-in", "transition": "fade"},
            ],
        },
        "segments": [
            {"start": 0, "end": 3, "text": "Hook forte nos primeiros segundos."},
            {"start": 3, "end": 10, "text": "Corpo do vídeo com detalhes."},
        ],
    }
    report = RetentionAnalyzer().analyze(payload)
    assert len(report.timeline) == 20
    assert report.timeline[0].second == 0
    assert report.hook_retention_pct >= 55
    assert report.overall_score > 0
    assert isinstance(report.recommendations, list)
    data = report.to_dict()
    assert "weak_segments" in data
    assert "drop_seconds" in data


def test_retention_detects_static_weak_segment():
    payload = {
        "duration_seconds": 12,
        "emotion": {"curiosity": 5, "retention": 5},
        "scenes": [{"label": "main", "start_seconds": 0, "end_seconds": 12}],
        "director_plan": {"segments": [{"movement": "static", "transition": "cut"}]},
    }
    report = RetentionAnalyzer().analyze(payload)
    assert report.weak_segments or report.completion_pct < 70


def test_extract_retention_prefers_retention_report():
    score, source = extract_retention(
        {
            "retention_report": {"overall_score": 82.5},
            "viral_report": {"retention_prediction": 50},
        }
    )
    assert score == 82.5
    assert source == "retention_report.overall_score"


def test_v5_autopilot_retention_after_quality():
    steps = PipelineStep.v5_media_autopilot_ordered()
    assert len(steps) == 16
    assert steps.index(PipelineStep.QUALITY) + 1 == steps.index(PipelineStep.RETENTION)


def test_factory_full_retention_after_quality():
    steps = PipelineStep.factory_full_ordered()
    assert PipelineStep.RETENTION in steps
    assert steps.index(PipelineStep.QUALITY) < steps.index(PipelineStep.RETENTION)


def test_retention_domain_event():
    assert STEP_TO_DOMAIN_EVENT["retention"] == RETENTION_ANALYZED


@pytest.mark.asyncio
async def test_retention_agent_handler():
    from contentos_agents.handlers.retention import RetentionAgentHandler
    from contentos_shared.schemas.agent import AgentTaskInput

    handler = RetentionAgentHandler()

    async def fake_store(_self, category, data, meta):
        return type("R", (), {"key": "scripts/retention.json", "bucket": "contentos", "id": uuid4()})()

    handler.get_asset_manager = lambda: type("M", (), {"store": fake_store})()

    output = await handler.execute(
        AgentTaskInput(
            job_id=uuid4(),
            project_id=uuid4(),
            pipeline_id=uuid4(),
            step="retention",
            payload={
                "topic": "test",
                "duration_seconds": 10,
                "scenes": [{"label": "a", "start_seconds": 0, "end_seconds": 10}],
            },
        )
    )
    assert output.data["retention_score"] > 0
    assert output.data["retention_report"]["timeline"]
