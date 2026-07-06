"""Tier B2 — Script Reviewer agent."""

from uuid import uuid4

from contentos_agents.handlers.script_review import _normalize_review, _normalize_script
from contentos_events.domain.event import DomainEvent
from contentos_events.domain.event_types import SCRIPT_REVIEW_FINISHED, STEP_TO_DOMAIN_EVENT
from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import get_builtin


def test_normalize_script_keeps_fallback_fields():
    original = {
        "title": "GTA 6",
        "hook": "Olha isso",
        "development": "Aconteceu X",
        "curiosity": "Mas tem um detalhe",
        "call_to_action": "Comenta aí",
        "full_text": "Olha isso. Aconteceu X. Mas tem um detalhe. Comenta aí",
        "duration_seconds": 40,
    }
    improved = _normalize_script(
        {"hook": "Para tudo", "duration_seconds": 90},
        original,
    )
    assert improved["hook"] == "Para tudo"
    assert improved["title"] == "GTA 6"
    assert improved["duration_seconds"] == 60


def test_normalize_review_scores_and_changes():
    original = {"title": "T", "hook": "H", "full_text": "H body", "duration_seconds": 45}
    review = _normalize_review(
        {
            "script": {"hook": "Novo hook", "full_text": "Novo hook body", "duration_seconds": 50},
            "changes": ["Hook mais forte", "CTA claro"],
            "score_before": 4,
            "score_after": 8,
            "summary": "Melhor retenção no início",
        },
        original,
    )
    assert review["script"]["hook"] == "Novo hook"
    assert review["score_before"] == 4
    assert review["score_after"] == 8
    assert len(review["changes"]) == 2


def test_v3_quality_includes_script_review_after_script():
    tpl = get_builtin("v3-quality")
    assert tpl is not None
    steps = tpl["steps"]
    assert steps.index("script") + 1 == steps.index("script_review")
    assert steps.index("script_review") + 1 == steps.index("emotion")
    assert len(steps) == 16
    assert tpl["config"]["enable_script_reviewer"] is True
    assert tpl["config"]["enable_emotion_analyzer"] is True
    assert tpl["config"]["enable_video_reviewer"] is True
    assert tpl["config"]["enable_storyboard"] is True
    assert [s.value for s in PipelineStep.v3_quality_ordered()] == steps


def test_script_review_domain_event():
    assert STEP_TO_DOMAIN_EVENT["script_review"] == SCRIPT_REVIEW_FINISHED
    event = DomainEvent.from_agent_callback(
        step="script_review",
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        status="completed",
    )
    assert event.event_type == SCRIPT_REVIEW_FINISHED
