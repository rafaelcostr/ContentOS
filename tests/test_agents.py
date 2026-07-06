"""Agent handler tests."""

import pytest
from contentos_shared.enums import PipelineStep


def test_nine_pipeline_steps():
    steps = PipelineStep.ordered()
    assert len(steps) == 9
    assert steps[0] == PipelineStep.RESEARCH
    assert steps[-1] == PipelineStep.PUBLISHER


def test_step_queue_names():
    for step in PipelineStep.ordered():
        assert step.value in (
            "research",
            "script",
            "scene",
            "takes",
            "voice",
            "subtitle",
            "editor",
            "quality",
            "publisher",
        )


def test_v2_pipeline_has_fourteen_steps():
    steps = PipelineStep.v2_ordered()
    assert len(steps) == 14
    assert steps[3] == PipelineStep.CLIP_RESEARCH
    assert steps[-1] == PipelineStep.ANALYTICS


def test_v3_pipeline_has_sixteen_steps():
    steps = PipelineStep.v3_quality_ordered()
    assert len(steps) == 16
    assert steps[0] == PipelineStep.TREND_INTELLIGENCE
    assert steps[1] == PipelineStep.RESEARCH
    assert steps.index(PipelineStep.STORYBOARD) + 1 == steps.index(PipelineStep.SCENE_DIRECTOR)
    assert steps.index(PipelineStep.SCENE_DIRECTOR) + 1 == steps.index(PipelineStep.TAKES)
