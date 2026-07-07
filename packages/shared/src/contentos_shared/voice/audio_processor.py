"""FFmpeg audio post-processing for voice profiles (V5.1.1)."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path


async def apply_speed_pitch(
    audio_bytes: bytes,
    *,
    speed: float = 1.0,
    pitch_semitones: float = 0.0,
) -> bytes:
    """Apply tempo and pitch adjustments. Returns original bytes if ffmpeg unavailable."""
    speed = max(0.5, min(2.0, speed))
    if abs(speed - 1.0) < 0.01 and abs(pitch_semitones) < 0.01:
        return audio_bytes
    if not audio_bytes:
        return audio_bytes
    try:
        return await _ffmpeg_filter(
            audio_bytes,
            _build_atempo_asetrate_filter(speed, pitch_semitones),
        )
    except Exception:
        return audio_bytes


async def concat_with_pauses(chunks: list[bytes], pause_ms: int) -> bytes:
    if not chunks:
        return b""
    if len(chunks) == 1:
        return chunks[0]
    pause_ms = max(0, min(2000, pause_ms))
    if pause_ms <= 0:
        return await _ffmpeg_concat(chunks)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            inputs: list[Path] = []
            for index, chunk in enumerate(chunks):
                path = tmp_path / f"chunk_{index}.mp3"
                path.write_bytes(chunk)
                inputs.append(path)
            silence = tmp_path / "silence.mp3"
            await _generate_silence(silence, pause_ms / 1000.0)
            sequence: list[Path] = []
            for index, path in enumerate(inputs):
                sequence.append(path)
                if index < len(inputs) - 1:
                    sequence.append(silence)
            output = tmp_path / "merged.mp3"
            await _concat_files(sequence, output)
            return output.read_bytes()
    except Exception:
        return chunks[0]


def _build_atempo_asetrate_filter(speed: float, pitch_semitones: float) -> str:
    filters: list[str] = []
    if abs(speed - 1.0) >= 0.01:
        filters.extend(_atempo_chain(speed))
    if abs(pitch_semitones) >= 0.01:
        factor = 2 ** (pitch_semitones / 12.0)
        filters.append(f"asetrate=44100*{factor:.6f},aresample=44100")
    if not filters:
        return "anull"
    return ",".join(filters)


def _atempo_chain(speed: float) -> list[str]:
    """FFmpeg atempo only accepts 0.5–2.0 per filter."""
    remaining = speed
    parts: list[str] = []
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append(f"atempo={remaining:.4f}")
    return parts


async def _ffmpeg_filter(audio_bytes: bytes, audio_filter: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "in.mp3"
        output_path = tmp_path / "out.mp3"
        input_path.write_bytes(audio_bytes)
        ffmpeg = os.getenv("FFMPEG_PATH", "ffmpeg")
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(input_path),
            "-af",
            audio_filter,
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(output_path),
        ]
        await _run(cmd)
        return output_path.read_bytes()


async def _ffmpeg_concat(chunks: list[bytes]) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        paths: list[Path] = []
        for index, chunk in enumerate(chunks):
            path = tmp_path / f"c{index}.mp3"
            path.write_bytes(chunk)
            paths.append(path)
        output = tmp_path / "out.mp3"
        await _concat_files(paths, output)
        return output.read_bytes()


async def _concat_files(paths: list[Path], output: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        list_path = Path(tmp) / "list.txt"
        lines = [f"file '{path.as_posix()}'" for path in paths]
        list_path.write_text("\n".join(lines), encoding="utf-8")
        ffmpeg = os.getenv("FFMPEG_PATH", "ffmpeg")
        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(output),
        ]
        await _run(cmd)


async def _generate_silence(path: Path, duration_seconds: float) -> None:
    ffmpeg = os.getenv("FFMPEG_PATH", "ffmpeg")
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-t",
        f"{duration_seconds:.3f}",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "4",
        str(path),
    ]
    await _run(cmd)


async def _run(cmd: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode(errors="replace")[-2000:])
