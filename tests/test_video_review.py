"""Tier B7 — Video Reviewer agent."""

from uuid import uuid4

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
