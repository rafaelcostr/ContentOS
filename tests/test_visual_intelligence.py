from contentos_autopilot.media import build_media_strategy_plan
from contentos_autopilot.visual import build_visual_pattern_snapshot


def test_visual_pattern_snapshot_summarizes_media_profiles() -> None:
    snapshot = build_visual_pattern_snapshot(
        project_id="project-1",
        channel_id="channel-1",
        media_profiles=[
            {
                "analysis": {
                    "scenario": "city street",
                    "motion": "fast",
                    "speed": "fast",
                    "angle": "close-up",
                    "colors": ["black", "gold"],
                    "emotion": "luxury",
                    "camera_type": "handheld",
                }
            },
            {
                "analysis": {
                    "scenario": "city street",
                    "motion": "pan-left",
                    "speed": "fast",
                    "angle": "wide",
                    "colors": ["black", "white"],
                    "emotion": "luxury",
                }
            },
        ],
    )

    data = snapshot.to_dict()
    assert data["confidence"] == "low"
    assert data["pacing"] == "fast"
    assert "city street" in data["scenarios"]
    assert "black" in data["colors"]
    assert "pan-left" in data["movements"]
    assert data["subtitle_style"]["avoid_full_screen_blocks"] is True


def test_media_strategy_accepts_visual_patterns() -> None:
    visual = build_visual_pattern_snapshot(
        project_id="project-1",
        media_profiles=[
            {"analysis": {"motion": "fast", "speed": "fast", "colors": ["red"], "scenario": "studio"}}
        ],
    )
    plan = build_media_strategy_plan(
        topic="carros de luxo",
        platform="tiktok",
        content_type="reel",
        visual_patterns=visual,
    )

    data = plan.to_dict()
    assert data["editor_hints"]["pacing"] == "fast"
    assert data["editor_hints"]["visual_patterns"]["colors"] == ["red"]
