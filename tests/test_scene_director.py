"""Tier B5 — Scene Director agent and director plan builder."""

from uuid import uuid4

from contentos_events.domain.event import DomainEvent
from contentos_events.domain.event_types import SCENE_DIRECTOR_FINISHED, STEP_TO_DOMAIN_EVENT
from contentos_shared.director_plan import build_director_plan, frame_to_directive
from contentos_shared.enums import PipelineStep
from contentos_shared.providers.ffmpeg_filters import RenderSpec, SceneSegment, scene_video_filter
from contentos_shared.workflow_templates import get_builtin


def test_frame_to_directive_zoom_in():
    directive = frame_to_directive(
        {"scene_index": 0, "movement": "zoom-in", "transition": "fade", "framing": "close-up"},
        pacing="medium",
    )
    assert directive["zoom_enabled"] is True
    assert directive["zoom_max"] >= 1.18
    assert directive["crop_bias"] == "top"
    assert directive["fade_in"] > 0


def test_frame_to_directive_static():
    directive = frame_to_directive({"movement": "static", "transition": "cut"}, pacing="fast")
    assert directive["zoom_enabled"] is False
    assert directive["fade_in"] < 0.2


def test_build_director_plan_from_storyboard():
    scenes = [
        {"label": "intro", "start_seconds": 0, "end_seconds": 5},
        {"label": "body", "start_seconds": 5, "end_seconds": 12},
    ]
    storyboard = {
        "overall_style": "cinematic",
        "frames": [
            {"scene_index": 0, "movement": "ken-burns", "transition": "fade", "framing": "medium"},
            {"scene_index": 1, "movement": "pan-left", "transition": "dissolve", "framing": "wide"},
        ],
    }
    plan = build_director_plan(storyboard=storyboard, scenes=scenes, emotion={"overall": 9})
    assert plan["pacing"] == "fast"
    assert plan["energy"] == 9
    assert len(plan["segments"]) == 2
    assert plan["segments"][1]["pan_x_expr"]
    assert plan["overall_style"] == "cinematic"


def test_build_director_plan_fallback_from_scenes():
    scenes = [{"label": "a", "start_seconds": 0, "end_seconds": 4}]
    plan = build_director_plan(storyboard={}, scenes=scenes, emotion={"overall": 3})
    assert plan["pacing"] == "slow"
    assert len(plan["segments"]) == 1


def test_v3_quality_includes_scene_director_after_storyboard():
    tpl = get_builtin("v3-quality")
    assert tpl is not None
    steps = tpl["steps"]
    assert steps.index("storyboard") + 1 == steps.index("scene_director")
    assert steps.index("scene_director") + 1 == steps.index("takes")
    assert len(steps) == 16
    assert tpl["config"]["enable_scene_director"] is True
    assert [s.value for s in PipelineStep.v3_quality_ordered()] == steps


def test_scene_director_domain_event():
    assert STEP_TO_DOMAIN_EVENT["scene_director"] == SCENE_DIRECTOR_FINISHED
    event = DomainEvent.from_agent_callback(
        step="scene_director",
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        status="completed",
    )
    assert event.event_type == SCENE_DIRECTOR_FINISHED


def test_scene_video_filter_uses_director_segment():
    spec = RenderSpec(enable_zoom=True, fade_duration=0.4)
    segment = SceneSegment(
        index=0,
        duration=5.0,
        zoom_enabled=False,
        fade_in=0.2,
        fade_out=0.3,
        crop_bias="top",
    )
    vf = scene_video_filter(spec, duration=5.0, segment=segment)
    assert "zoompan" not in vf
    assert "fade=t=in:st=0:d=0.2" in vf
    assert "(ih-1920)/4" in vf
