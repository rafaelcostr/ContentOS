"""Tier B4 — Storyboard AI agent."""

from uuid import uuid4

from contentos_agents.handlers.storyboard import normalize_storyboard
from contentos_events.domain.event import DomainEvent
from contentos_events.domain.event_types import STEP_TO_DOMAIN_EVENT, STORYBOARD_FINISHED
from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import get_builtin


def test_normalize_storyboard_from_llm():
    scenes = [{"label": "intro", "start_seconds": 0, "end_seconds": 5}]
    board = normalize_storyboard(
        {
            "overall_style": "cinematic",
            "frames": [
                {
                    "scene_index": 0,
                    "scene_label": "intro",
                    "framing": "close-up",
                    "movement": "zoom-in",
                    "transition": "fade",
                    "duration_seconds": 5,
                    "visual_notes": "Rosto em choque",
                    "b_roll_hint": "olho",
                }
            ],
        },
        scenes,
    )
    assert board["overall_style"] == "cinematic"
    assert board["frames"][0]["framing"] == "close-up"
    assert board["frames"][0]["movement"] == "zoom-in"


def test_normalize_invalid_enums_fall_back():
    board = normalize_storyboard(
        {"frames": [{"framing": "ultra", "movement": "spin", "transition": "wipe"}]},
        [{"label": "a", "start_seconds": 0, "end_seconds": 4}],
    )
    frame = board["frames"][0]
    assert frame["framing"] == "medium"
    assert frame["movement"] == "static"
    assert frame["transition"] == "cut"


def test_normalize_fallback_from_scenes():
    scenes = [
        {"label": "a", "start_seconds": 0, "end_seconds": 3, "description": "A"},
        {"label": "b", "start_seconds": 3, "end_seconds": 8, "visual_hint": "B"},
    ]
    board = normalize_storyboard({}, scenes)
    assert len(board["frames"]) == 2
    assert board["frames"][1]["scene_label"] == "b"


def test_v3_quality_includes_storyboard_after_scene():
    tpl = get_builtin("v3-quality")
    assert tpl is not None
    steps = tpl["steps"]
    assert steps.index("scene") + 1 == steps.index("storyboard")
    assert steps.index("storyboard") + 1 == steps.index("scene_director")
    assert steps.index("scene_director") + 1 == steps.index("takes")
    assert len(steps) == 16
    assert tpl["config"]["enable_storyboard"] is True
    assert [s.value for s in PipelineStep.v3_quality_ordered()] == steps


def test_storyboard_domain_event():
    assert STEP_TO_DOMAIN_EVENT["storyboard"] == STORYBOARD_FINISHED
    event = DomainEvent.from_agent_callback(
        step="storyboard",
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        status="completed",
    )
    assert event.event_type == STORYBOARD_FINISHED
