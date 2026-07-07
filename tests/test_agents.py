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


def test_v2_pipeline_has_asset_search_step():
    steps = PipelineStep.v2_ordered()
    assert len(steps) == 16
    assert steps[3] == PipelineStep.CLIP_RESEARCH
    assert steps.index(PipelineStep.ASSET_SEARCH) + 1 == steps.index(PipelineStep.TAKES)
    assert steps[-1] == PipelineStep.ANALYTICS


def test_v3_pipeline_has_sixteen_steps():
    steps = PipelineStep.v3_quality_ordered()
    assert len(steps) == 16
    assert steps[0] == PipelineStep.TREND_INTELLIGENCE
    assert steps[1] == PipelineStep.RESEARCH
    assert steps.index(PipelineStep.STORYBOARD) + 1 == steps.index(PipelineStep.SCENE_DIRECTOR)
    assert steps.index(PipelineStep.SCENE_DIRECTOR) + 1 == steps.index(PipelineStep.TAKES)


def test_factory_full_pipeline_uses_executable_factory_order():
    steps = PipelineStep.factory_full_ordered()
    assert len(steps) == 31
    assert steps.index(PipelineStep.EDITOR) < steps.index(PipelineStep.RETENTION)
    assert steps.index(PipelineStep.QUALITY) < steps.index(PipelineStep.RETENTION)
    assert steps[0] == PipelineStep.RESEARCH
    assert steps.index(PipelineStep.TREND_INTELLIGENCE) < steps.index(PipelineStep.HOOK)
    assert steps.index(PipelineStep.CLIP_RESEARCH) < steps.index(PipelineStep.ASSET_COLLECTOR)
    assert steps.index(PipelineStep.ASSET_SEARCH) + 1 == steps.index(PipelineStep.TAKES)
    assert steps.index(PipelineStep.THUMBNAIL) < steps.index(PipelineStep.QUALITY)
    assert steps.index(PipelineStep.VIDEO_REVIEW) + 1 == steps.index(PipelineStep.AUTO_RETRY)
    assert steps.index(PipelineStep.AUTO_RETRY) + 1 == steps.index(PipelineStep.CONTENT_SCORE)
    assert steps.index(PipelineStep.CONTENT_SCORE) + 1 == steps.index(PipelineStep.AI_DIRECTOR)
    assert steps.index(PipelineStep.AI_DIRECTOR) + 1 == steps.index(PipelineStep.CONTENT_INTELLIGENCE)
    assert steps.index(PipelineStep.CONTENT_INTELLIGENCE) < steps.index(PipelineStep.LEARNING)
    assert steps.index(PipelineStep.LEARNING) + 1 == steps.index(PipelineStep.KNOWLEDGE_BASE)
    assert steps.index(PipelineStep.KNOWLEDGE_BASE) + 1 == steps.index(PipelineStep.CREATIVE_MEMORY)
    assert steps.index(PipelineStep.CREATIVE_MEMORY) + 1 == steps.index(PipelineStep.ANALYTICS)
    assert steps[-1] == PipelineStep.PUBLISHER
