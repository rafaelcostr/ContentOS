"""FFmpeg filter builder unit tests."""

from pathlib import Path

from contentos_shared.providers.ffmpeg_filters import (
    RenderSpec,
    SceneSegment,
    build_audio_mix_filter,
    placeholder_video_filter,
    scene_video_filter,
    subtitle_and_progress_filter,
)


def test_scene_video_filter_includes_zoom_and_fade():
    spec = RenderSpec(width=1080, height=1920, fps=60, enable_zoom=True, fade_duration=0.4)
    vf = scene_video_filter(spec, duration=5.0)
    assert "zoompan" in vf
    assert "fade=t=in" in vf
    assert "fade=t=out" in vf
    assert "1080" in vf and "1920" in vf


def test_scene_video_filter_no_zoom():
    spec = RenderSpec(enable_zoom=False, fps=60)
    vf = scene_video_filter(spec, duration=3.0)
    assert "zoompan" not in vf
    assert "fps=60" in vf


def test_subtitle_and_progress_filter():
    spec = RenderSpec(total_duration=30.0, progress_bar_height=8)
    vf = subtitle_and_progress_filter(None, spec)
    assert "drawbox" in vf
    assert "30.0" in vf or "30" in vf


def test_subtitle_with_srt_path(tmp_path):
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello", encoding="utf-8")
    spec = RenderSpec(total_duration=10.0)
    vf = subtitle_and_progress_filter(srt, spec)
    assert "subtitles=" in vf
    assert "FontSize=26" in vf


def test_audio_mix_without_music():
    assert "[aout]" in build_audio_mix_filter(False, 0.12)
    assert "amix" not in build_audio_mix_filter(False, 0.12)


def test_audio_mix_with_music():
    af = build_audio_mix_filter(True, 0.15)
    assert "amix" in af
    assert "0.15" in af


def test_render_spec_defaults():
    spec = RenderSpec()
    assert spec.width == 1080
    assert spec.height == 1920
    assert spec.fps == 60


def test_scene_segment():
    seg = SceneSegment(index=0, duration=5.0, label="intro")
    assert seg.duration == 5.0
