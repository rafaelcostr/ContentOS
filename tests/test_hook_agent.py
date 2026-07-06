"""Tier B1 — Hook Generator agent."""

from uuid import uuid4

from contentos_agents.handlers.hook import HOOK_STYLES, _normalize_hook
from contentos_events.domain.event import DomainEvent
from contentos_events.domain.event_types import HOOK_FINISHED, STEP_TO_DOMAIN_EVENT
from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import get_builtin


def test_normalize_hook_defaults():
    hook = _normalize_hook({}, "GTA 6")
    assert hook["style"] == "curiosity"
    assert "GTA 6" in hook["hook_text"]
    assert isinstance(hook["alternatives"], list)


def test_normalize_hook_valid_styles():
    for style in HOOK_STYLES:
        hook = _normalize_hook({"style": style, "hook_text": "Abre com isso"}, "tema")
        assert hook["style"] == style
        assert hook["hook_text"] == "Abre com isso"


def test_normalize_hook_invalid_style_falls_back():
    hook = _normalize_hook({"style": "random", "hook_text": "Oi"}, "x")
    assert hook["style"] == "curiosity"


def test_v3_quality_template_has_hook_before_script():
    tpl = get_builtin("v3-quality")
    assert tpl is not None
    steps = tpl["steps"]
    assert steps[0] == "trend_intelligence"
    assert steps[1] == "research"
    assert steps[2] == "hook"
    assert steps[3] == "script"
    assert steps[4] == "script_review"
    assert steps[5] == "emotion"
    assert steps[-2] == "video_review"
    assert steps[-1] == "publisher"
    assert "storyboard" in steps
    assert len(steps) == 16
    assert tpl["config"]["enable_hook_generator"] is True
    assert tpl["config"]["enable_script_reviewer"] is True
    assert tpl["config"]["enable_emotion_analyzer"] is True
    assert tpl["config"]["enable_video_reviewer"] is True
    assert tpl["config"]["enable_storyboard"] is True


def test_v3_quality_ordered_matches_template():
    assert [s.value for s in PipelineStep.v3_quality_ordered()] == get_builtin("v3-quality")["steps"]


def test_hook_domain_event():
    assert STEP_TO_DOMAIN_EVENT["hook"] == HOOK_FINISHED
    event = DomainEvent.from_agent_callback(
        step="hook",
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        status="completed",
        payload={"hook_style": "mystery"},
    )
    assert event.event_type == HOOK_FINISHED
