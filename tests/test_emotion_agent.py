"""Tier B3 — Emotion Analyzer agent."""

from uuid import uuid4

from contentos_agents.handlers.emotion import _heuristic_scores, normalize_emotion_scores
from contentos_events.domain.event import DomainEvent
from contentos_events.domain.event_types import EMOTION_FINISHED, STEP_TO_DOMAIN_EVENT
from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import get_builtin


def test_normalize_emotion_scores():
    scores = normalize_emotion_scores(
        {
            "emotion": 9,
            "curiosity": 8,
            "retention": 7,
            "impact": 8,
            "overall": 8,
            "dominant_emotion": "Surpresa",
            "risks": ["CTA fraco"],
            "strengths": ["Hook forte"],
            "summary": "Bom potencial",
        },
        script={"hook": "x"},
        hook_text="x",
    )
    assert scores["emotion"] == 9
    assert scores["dominant_emotion"] == "surpresa"
    assert scores["risks"] == ["CTA fraco"]


def test_normalize_clamps_and_computes_overall():
    scores = normalize_emotion_scores(
        {"emotion": 12, "curiosity": 0, "retention": 5, "impact": 5},
        script={},
        hook_text="",
    )
    assert scores["emotion"] == 10
    assert scores["curiosity"] == 1
    assert 1 <= scores["overall"] <= 10


def test_heuristic_fallback():
    scores = _heuristic_scores(
        {"hook": "Você sabia?", "full_text": "Você sabia? Isso muda tudo agora."},
        "Você sabia?",
    )
    assert scores["curiosity"] >= 5
    assert scores["overall"] >= 1


def test_v3_quality_includes_emotion_after_script_review():
    tpl = get_builtin("v3-quality")
    assert tpl is not None
    steps = tpl["steps"]
    assert steps.index("script_review") + 1 == steps.index("emotion")
    assert "video_review" in steps
    assert len(steps) == 16
    assert tpl["config"]["enable_emotion_analyzer"] is True
    assert tpl["config"]["enable_video_reviewer"] is True
    assert tpl["config"]["enable_storyboard"] is True
    assert [s.value for s in PipelineStep.v3_quality_ordered()] == steps


def test_emotion_domain_event():
    assert STEP_TO_DOMAIN_EVENT["emotion"] == EMOTION_FINISHED
    event = DomainEvent.from_agent_callback(
        step="emotion",
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        status="completed",
        payload={"emotion_overall": 8},
    )
    assert event.event_type == EMOTION_FINISHED
