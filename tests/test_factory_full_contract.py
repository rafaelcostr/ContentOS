"""Factory-full pipeline contract tests.

These tests keep the executable assembly line synchronized across the shared
pipeline enum, built-in template, workflow queues, worker handlers and domain
events.
"""

from contentos_events.domain.event_types import STEP_TO_DOMAIN_EVENT
from contentos_shared.enums import PipelineStep
from contentos_shared.factory_map import executable_factory_steps
from contentos_shared.workflow_templates import FACTORY_FULL_STEPS, get_builtin
from contentos_workflow.engine import STEP_QUEUE_MAP


def _factory_steps() -> list[str]:
    return [step.value for step in PipelineStep.factory_full_ordered()]


def test_factory_full_sources_share_one_step_order():
    steps = _factory_steps()
    template = get_builtin("factory-full")

    assert template is not None
    assert len(steps) == 29
    assert FACTORY_FULL_STEPS == steps
    assert template["steps"] == steps
    assert [step.value for step in executable_factory_steps()] == steps
    assert "clip_research" not in steps
    assert "asset_collector" not in steps


def test_factory_full_steps_have_queues_handlers_and_events():
    from contentos_agents.worker import HANDLERS

    missing_queue = [step for step in _factory_steps() if step not in STEP_QUEUE_MAP]
    missing_handler = [step for step in _factory_steps() if step not in HANDLERS]
    missing_event = [step for step in _factory_steps() if step not in STEP_TO_DOMAIN_EVENT]

    assert missing_queue == []
    assert missing_handler == []
    assert missing_event == []


def test_factory_full_queue_names_match_step_names():
    for step in _factory_steps():
        assert STEP_QUEUE_MAP[step] == f"contentos.{step}"


def test_factory_full_template_enables_required_factory_features():
    template = get_builtin("factory-full")
    assert template is not None
    config = template["config"]

    expected_flags = [
        "enable_media_analyze",
        "enable_take_recommendation",
        "enable_thumbnail",
        "enable_analytics_ai",
        "enable_auto_retry",
        "enable_content_score",
        "enable_learning",
        "enable_knowledge_base",
        "enable_retention",
        "enable_seo",
        "enable_ai_director",
        "enable_creative_memory",
    ]

    disabled = [flag for flag in expected_flags if config.get(flag) is not True]
    assert disabled == []
    assert "enable_clip_pipeline" not in config
