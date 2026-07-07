"""V5.1.3 — Cinematic Editor (speed ramp, ducking, presets)."""

from contentos_shared.cinematic import (
    CinematicSettings,
    apply_directive_to_segment,
    normalize_playback_speed,
)
from contentos_shared.director_plan import frame_to_directive
from contentos_shared.providers.ffmpeg_filters import (
    RenderSpec,
    SceneSegment,
    build_audio_mix_filter,
    scene_video_filter,
    speed_filter_expr,
)


def test_normalize_playback_speed_clamps():
    assert normalize_playback_speed(3.0) == 2.0
    assert normalize_playback_speed(0.1) == 0.5
    assert normalize_playback_speed("1.2") == 1.2
    assert normalize_playback_speed("bad") == 1.0


def test_cinematic_settings_from_payload():
    settings = CinematicSettings.from_payload(
        {"cinematic": {"preset": "punchy", "enable_ducking": True, "music_volume": 0.18}}
    )
    assert settings.preset == "punchy"
    assert settings.music_volume == 0.18
    assert settings.ducking_ratio == 12.0


def test_cinematic_settings_apply_to_render_spec():
    spec = RenderSpec()
    CinematicSettings(
        enable_zoom=False,
        enable_ducking=True,
        music_volume=0.2,
        ducking_ratio=10.0,
        ducking_threshold=0.025,
    ).apply_to_render_spec(spec)
    assert spec.enable_zoom is False
    assert spec.enable_ducking is True
    assert spec.music_volume == 0.2
    assert spec.ducking_ratio == 10.0


def test_apply_directive_to_segment_speed():
    segment = SceneSegment(index=0, duration=4.0)
    apply_directive_to_segment(
        segment,
        {"playback_speed": 1.0, "speed_ramp_end": 1.35, "zoom_enabled": True},
    )
    assert segment.playback_speed == 1.0
    assert segment.speed_ramp_end == 1.35
    assert segment.zoom_enabled is True


def test_frame_to_directive_speed_ramp_up():
    directive = frame_to_directive({"movement": "speed-ramp-up"}, pacing="medium")
    assert directive["playback_speed"] == 1.0
    assert directive["speed_ramp_end"] == 1.35


def test_frame_to_directive_slow_mo():
    directive = frame_to_directive({"movement": "slow-mo"}, pacing="slow")
    assert directive["playback_speed"] == 0.75
    assert "speed_ramp_end" not in directive


def test_speed_filter_expr_constant():
    seg = SceneSegment(index=0, duration=5.0, playback_speed=1.25)
    assert speed_filter_expr(seg, 5.0, 60) == "setpts=PTS/1.2500"


def test_speed_filter_expr_ramp():
    seg = SceneSegment(index=0, duration=5.0, playback_speed=1.0, speed_ramp_end=1.35)
    expr = speed_filter_expr(seg, 5.0, 60)
    assert expr is not None
    assert "setpts=" in expr
    assert "1.3500" in expr
    assert "300" in expr


def test_scene_video_filter_includes_speed_ramp():
    spec = RenderSpec(enable_zoom=False, fps=60)
    segment = SceneSegment(index=0, duration=5.0, playback_speed=0.8)
    vf = scene_video_filter(spec, duration=5.0, segment=segment)
    assert "setpts=PTS/0.8000" in vf


def test_audio_mix_ducking_enabled():
    af = build_audio_mix_filter(True, 0.12, enable_ducking=True, ducking_ratio=8.0)
    assert "sidechaincompress" in af
    assert "amix" in af


def test_audio_mix_ducking_disabled():
    af = build_audio_mix_filter(True, 0.12, enable_ducking=False)
    assert "sidechaincompress" not in af
    assert "amix" in af


def test_cinematic_disabled_via_env(monkeypatch):
    monkeypatch.setenv("ENABLE_CINEMATIC_EDITOR", "false")
    settings = CinematicSettings.from_payload({})
    assert settings.enable_ducking is False
