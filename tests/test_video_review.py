"""Tier B7 — Video Reviewer agent."""

from uuid import uuid4

import pytest
from contentos_agents.handlers.video_review import _heuristic_review, normalize_video_review
from contentos_events.domain.event import DomainEvent
from contentos_events.domain.event_types import STEP_TO_DOMAIN_EVENT, VIDEO_REVIEW_FINISHED
from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import get_builtin


def test_normalize_video_review():
    review = normalize_video_review(
        {
            "score": 9,
            "passed": True,
            "dimensions": {"hook": 9, "pacing": 8, "emotion": 9, "cta": 8, "technical": 9},
            "suggestions": ["Manter ritmo"],
            "summary": "Pronto para publicar",
        },
        emotion={"overall": 8},
        quality_passed=True,
        render_meta={"duration_seconds": 40},
    )
    assert review["score"] == 9
    assert review["passed"] is True
    assert review["dimensions"]["hook"] == 9


def test_heuristic_fails_when_quality_failed():
    review = _heuristic_review(
        emotion={"overall": 9, "curiosity": 9, "retention": 9, "emotion": 9, "impact": 9},
        quality_passed=False,
        render_meta={"duration_seconds": 40},
    )
    assert review["score"] <= 4
    assert review["passed"] is False


def test_v3_quality_includes_video_review_before_publisher():
    tpl = get_builtin("v3-quality")
    assert tpl is not None
    steps = tpl["steps"]
    assert steps.index("quality") + 1 == steps.index("video_review")
    assert steps.index("video_review") + 1 == steps.index("publisher")
    assert "storyboard" in steps
    assert len(steps) == 16
    assert tpl["config"]["enable_video_reviewer"] is True
    assert tpl["config"]["enable_storyboard"] is True
    assert [s.value for s in PipelineStep.v3_quality_ordered()] == steps


def test_video_review_domain_event():
    assert STEP_TO_DOMAIN_EVENT["video_review"] == VIDEO_REVIEW_FINISHED
    event = DomainEvent.from_agent_callback(
        step="video_review",
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        status="completed",
        payload={"video_score": 8},
    )
    assert event.event_type == VIDEO_REVIEW_FINISHED


@pytest.mark.asyncio
async def test_video_review_job_completes_when_score_fails(monkeypatch):
    """Job status is COMPLETED even when review fails — engine handles retry (ADR-006)."""
    from contentos_agents.handlers.video_review import VideoReviewAgentHandler
    from contentos_shared.enums import JobStatus
    from contentos_shared.schemas.agent import AgentTaskInput

    monkeypatch.setenv("VIDEO_REVIEW_MIN_SCORE", "8")

    class _FakeAM:
        async def store(self, *args, **kwargs):
            return type("Ref", (), {"id": uuid4()})()

    class _FakeHandler(VideoReviewAgentHandler):
        def get_asset_manager(self):
            return _FakeAM()

        async def chat_json_with_cache(self, *args, **kwargs):
            return (
                {
                    "score": 4,
                    "passed": False,
                    "dimensions": {"hook": 4, "pacing": 4, "emotion": 4, "cta": 4, "technical": 4},
                    "suggestions": ["Melhorar hook"],
                    "summary": "Abaixo do mínimo",
                },
                False,
                "cache-key",
            )

        def render_prompt(self, *args, **kwargs):
            class _Prompt:
                version = 1
                system = ""
                user = ""

            return _Prompt()

    handler = _FakeHandler()
    task = AgentTaskInput(
        job_id=uuid4(),
        project_id=uuid4(),
        pipeline_id=uuid4(),
        step="video_review",
        payload={
            "topic": "GTA 6",
            "script": {"title": "GTA 6"},
            "emotion": {"overall": 5, "curiosity": 5, "retention": 5, "emotion": 5, "impact": 5},
            "quality_passed": True,
            "quality_score": 8,
        },
    )
    output = await handler.execute(task)
    assert output.status == JobStatus.COMPLETED.value
    assert output.data["video_review_passed"] is False
    assert output.data["video_score"] == 4
