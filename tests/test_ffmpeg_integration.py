"""Optional FFmpeg integration — 9:16 vertical render proof (phase 5)."""

import shutil
from pathlib import Path

import pytest
from contentos_shared.providers.ffmpeg_filters import RenderSpec, SceneSegment
from contentos_shared.providers.ffmpeg_provider import FFmpegProvider
from contentos_shared.quality_scoring import quality_min_bitrate_bps

pytestmark = pytest.mark.ffmpeg


@pytest.fixture
def ffmpeg_available():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")


@pytest.mark.asyncio
async def test_render_timeline_probe_9_16(ffmpeg_available, tmp_path):
    provider = FFmpegProvider()
    tiny_clip = tmp_path / "clip.mp4"
    await provider.create_placeholder(tiny_clip, duration=3)

    audio = tmp_path / "audio.m4a"
    await provider._generate_ambient_music(audio, 3.0)

    output = tmp_path / "render.mp4"
    spec = RenderSpec(
        width=1080,
        height=1920,
        fps=60,
        total_duration=3.0,
        scenes=[SceneSegment(index=0, duration=3.0, clip_path=tiny_clip, label="main")],
        enable_zoom=False,
        fade_duration=0.2,
    )
    await provider.render_timeline(spec, audio, None, output, music_path=None)

    probe = await provider.probe(output)
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    assert int(video["width"]) == 1080
    assert int(video["height"]) == 1920
    assert video.get("codec_name") in {"h264", "avc1"}
    duration = float(probe["format"]["duration"])
    assert 2.5 <= duration <= 4.5
    bit_rate = int(probe["format"].get("bit_rate") or 0)
    assert bit_rate >= quality_min_bitrate_bps(), f"bitrate {bit_rate} below QA minimum"
