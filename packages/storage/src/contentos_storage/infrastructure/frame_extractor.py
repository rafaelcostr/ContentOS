"""Extract JPEG frames from video bytes via FFmpeg."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path


async def extract_frame_jpegs(video_bytes: bytes, *, max_frames: int = 2) -> list[bytes]:
    """Return up to max_frames JPEG stills (start + midpoint)."""
    ffmpeg = os.getenv("FFMPEG_PATH", "ffmpeg")
    ffprobe = os.getenv("FFPROBE_PATH", "ffprobe")
    frames: list[bytes] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        video_path = tmp_path / "input.mp4"
        video_path.write_bytes(video_bytes)
        duration = await _probe_duration(ffprobe, video_path)
        timestamps = _sample_timestamps(duration, max_frames)

        for index, ts in enumerate(timestamps):
            out = tmp_path / f"frame_{index}.jpg"
            cmd = [
                ffmpeg,
                "-y",
                "-ss",
                str(ts),
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(out),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0 or not out.exists():
                continue
            frames.append(out.read_bytes())
    return frames


async def _probe_duration(ffprobe: str, path: Path) -> float:
    import json

    cmd = [
        ffprobe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        str(path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        return 3.0
    try:
        data = json.loads(stdout.decode())
        return max(float(data.get("format", {}).get("duration", 3.0)), 1.0)
    except (json.JSONDecodeError, ValueError, TypeError):
        return 3.0


def _sample_timestamps(duration: float, max_frames: int) -> list[float]:
    if max_frames <= 1:
        return [min(1.0, duration * 0.1)]
    mid = max(duration * 0.5, 0.5)
    start = min(1.0, duration * 0.1)
    return [start, mid][:max_frames]
