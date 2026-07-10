"""Quality Agent — 0–10 technical scoring."""

from contentos_shared.quality_scoring import build_quality_report, quality_min_score


def test_perfect_quality_score():
    report = build_quality_report(
        has_render=True,
        render_exists=True,
        render_size_ok=True,
        has_audio_ref=True,
        has_audio_stream=True,
        has_subtitles=True,
        subtitle_sync_skipped=False,
        width=1080,
        height=1920,
        codec="h264",
        fps=60.0,
        duration=45.0,
    )
    assert report.score == 10
    assert report.passed is True
    assert len(report.dimensions) == 7


def test_failed_quality_missing_render():
    report = build_quality_report(
        has_render=False,
        render_exists=False,
        render_size_ok=False,
        has_audio_ref=False,
        has_audio_stream=False,
        has_subtitles=False,
        subtitle_sync_skipped=False,
    )
    assert report.score <= 3
    assert report.passed is False
    assert report.errors


def test_partial_framerate_score():
    report = build_quality_report(
        has_render=True,
        render_exists=True,
        render_size_ok=True,
        has_audio_ref=True,
        has_audio_stream=True,
        has_subtitles=True,
        subtitle_sync_skipped=False,
        width=1080,
        height=1920,
        codec="h264",
        fps=45.0,
        duration=40.0,
    )
    assert report.dimensions["framerate"] == 5
    assert report.score < 10


def test_duration_under_30_seconds_is_short():
    report = build_quality_report(
        has_render=True,
        render_exists=True,
        render_size_ok=True,
        has_audio_ref=True,
        has_audio_stream=True,
        has_subtitles=True,
        subtitle_sync_skipped=False,
        width=1080,
        height=1920,
        codec="h264",
        fps=60.0,
        duration=27.2,
    )
    assert report.dimensions["duration"] == 6
    assert report.score < 10


def test_quality_min_score_env(monkeypatch):
    monkeypatch.setenv("QUALITY_MIN_SCORE", "9")
    assert quality_min_score() == 9


def test_subtitle_sync_skipped_passes_subtitles_dim():
    report = build_quality_report(
        has_render=True,
        render_exists=True,
        render_size_ok=True,
        has_audio_ref=True,
        has_audio_stream=True,
        has_subtitles=False,
        subtitle_sync_skipped=True,
        width=1080,
        height=1920,
        codec="h264",
        fps=60.0,
        duration=30.0,
    )
    assert report.dimensions["subtitles"] == 10


def test_loudness_in_range_passes():
    report = build_quality_report(
        has_render=True,
        render_exists=True,
        render_size_ok=True,
        has_audio_ref=True,
        has_audio_stream=True,
        has_subtitles=True,
        subtitle_sync_skipped=False,
        width=1080,
        height=1920,
        codec="h264",
        fps=60.0,
        duration=30.0,
        integrated_lufs=-16.2,
    )
    assert report.dimensions["loudness"] == 10
    assert report.passed is True


def test_loudness_out_of_range_is_soft_signal():
    """Loudness lowers score + adds suggestion but never hard-blocks (no error)."""
    report = build_quality_report(
        has_render=True,
        render_exists=True,
        render_size_ok=True,
        has_audio_ref=True,
        has_audio_stream=True,
        has_subtitles=True,
        subtitle_sync_skipped=False,
        width=1080,
        height=1920,
        codec="h264",
        fps=60.0,
        duration=30.0,
        integrated_lufs=-28.0,
    )
    assert report.dimensions["loudness"] < 10
    assert not any("Loudness" in err for err in report.errors)
    assert report.passed is True
    assert any("loudness" in s.lower() for s in report.suggestions)


def test_quality_scoring_adds_real_media_dimensions():
    report = build_quality_report(
        has_render=True,
        render_exists=True,
        render_size_ok=True,
        has_audio_ref=True,
        has_audio_stream=True,
        has_subtitles=True,
        subtitle_sync_skipped=False,
        width=1080,
        height=1920,
        codec="h264",
        fps=60.0,
        duration=30.0,
        has_real_clips=False,
        missing_clip_count=2,
        has_narration_audio=False,
        extra_errors=["Render contains placeholder scenes", "Render used generated/silent narration audio"],
    )
    assert report.passed is False
    assert report.dimensions["real_clips"] == 0
    assert report.dimensions["narration"] == 0
    assert "Substituir cenas placeholder por clipes reais" in report.suggestions
