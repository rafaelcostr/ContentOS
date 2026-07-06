"""Tests for V2 dynamic pipeline step routing."""

from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import get_builtin


def test_v2_dynamic_step_order_matches_architecture():
    tpl = get_builtin("v2-dynamic")
    assert tpl is not None
    expected = [s.value for s in PipelineStep.v2_ordered()]
    assert tpl["steps"] == expected


def test_engine_queue_map_covers_v2_steps():
    from contentos_workflow.engine import STEP_QUEUE_MAP

    for step in PipelineStep.v2_ordered():
        assert step.value in STEP_QUEUE_MAP
