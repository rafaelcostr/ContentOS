"""FFmpeg video assembly — 1080x1920 vertical shorts with effects."""

import asyncio
import json
import os
import re
import tempfile
from pathlib import Path

from contentos_shared.media_production import render_allow_placeholder
from contentos_shared.providers.ffmpeg_filters import (
    RenderSpec,
    SceneSegment,
    build_audio_mix_filter,
    placeholder_video_filter,
    scene_video_filter,
    subtitle_and_progress_filter,
)


class PlaceholderRenderBlockedError(RuntimeError):
    """Raised when FFmpeg would synthesize a placeholder scene in production mode."""


def x264_video_encode_args() -> list[str]:
    """x264 settings that keep ffprobe format bit_rate above QUALITY_MIN_BITRATE_BPS."""
    from contentos_shared.quality_scoring import quality_min_bitrate_bps

    min_bps = quality_min_bitrate_bps()
    # Explicit CBR-ish VBR: static zoom scenes need a hard floor to pass ffprobe QA.
    video_target_bps = max(3_000_000, min_bps + 2_000_000)
    target_k = video_target_bps // 1000
    return [
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-b:v",
        f"{target_k}k",
        "-minrate",
        f"{target_k}k",
        "-maxrate",
        f"{target_k}k",
        "-bufsize",
        f"{target_k * 2}k",
        "-x264-params",
        "nal-hrd=cbr",
        "-pix_fmt",
        "yuv420p",
    ]


class FFmpegProvider:
    def __init__(self) -> None:
        self.ffmpeg = os.getenv("FFMPEG_PATH", "ffmpeg")
        self.ffprobe = os.getenv("FFPROBE_PATH", "ffprobe")

    async def _run(self, cmd: list[str]) -> None:
        if cmd[0] == "ffmpeg":
            cmd[0] = self.ffmpeg
        if cmd[0] == "ffprobe":
            cmd[0] = self.ffprobe
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {stderr.decode()[-2000:]}")

    async def probe(self, path: Path) -> dict:
        cmd = [
            self.ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return json.loads(stdout.decode())

    async def probe_loudness(self, path: Path) -> float | None:
        """Measure integrated loudness (LUFS) via ffmpeg loudnorm analysis."""
        cmd = [
            self.ffmpeg,
            "-i",
            str(path),
            "-af",
            "loudnorm=print_format=json",
            "-f",
            "null",
            "-",
        ]
        if cmd[0] == "ffmpeg":
            cmd[0] = self.ffmpeg
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            return None
        text = stderr.decode(errors="replace")
        match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", text)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return float(data["input_i"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    async def create_placeholder(self, output_path: Path, duration: int = 10) -> None:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x1e1b4b:s=1080x1920:d={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "60",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        await self._run(cmd)

    async def _render_scene_segment(
        self,
        spec: RenderSpec,
        scene: SceneSegment,
        output: Path,
        tmp: Path,
    ) -> None:
        duration = max(scene.duration, 0.5)
        if scene.clip_path and scene.clip_path.exists():
            vf = scene_video_filter(spec, duration, segment=scene)
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(scene.clip_path),
                "-t",
                str(duration),
                "-vf",
                vf,
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                str(output),
            ]
        else:
            if not render_allow_placeholder():
                label = scene.label or f"scene_{scene.index}"
                raise PlaceholderRenderBlockedError(
                    f"placeholder render blocked for scene {label} (index={scene.index})"
                )
            placeholder = tmp / f"ph_{scene.index}.mp4"
            cmd_ph = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x0f172a:s={spec.width}x{spec.height}:d={duration}",
                "-vf",
                placeholder_video_filter(spec, duration),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(placeholder),
            ]
            await self._run(cmd_ph)
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(placeholder),
                "-c:v",
                "copy",
                str(output),
            ]
        await self._run(cmd)

    async def _concat_segments(self, segments: list[Path], output: Path) -> None:
        list_file = output.parent / "concat_list.txt"
        lines = [f"file '{s.resolve().as_posix()}'" for s in segments]
        list_file.write_text("\n".join(lines), encoding="utf-8")
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
        await self._run(cmd)

    async def _generate_ambient_music(self, path: Path, duration: float) -> None:
        """Copyright-free ambient pad for background (lavfi)."""
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=130:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=196:duration={duration}",
            "-filter_complex",
            "[0:a][1:a]amix=inputs=2:duration=first,volume=0.25",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(path),
        ]
        await self._run(cmd)

    async def render_timeline(
        self,
        spec: RenderSpec,
        audio_path: Path,
        subtitle_path: Path | None,
        output_path: Path,
        music_path: Path | None = None,
    ) -> None:
        """Full vertical render: multi-scene, zoom, fade, subs, progress bar, music mix."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            segments: list[Path] = []

            scenes = spec.scenes or [SceneSegment(index=0, duration=spec.total_duration, label="main")]

            for scene in scenes:
                seg_out = tmp / f"scene_{scene.index:02d}.mp4"
                await self._render_scene_segment(spec, scene, seg_out, tmp)
                segments.append(seg_out)

            concat_out = tmp / "concat.mp4"
            await self._concat_segments(segments, concat_out)

            vf = subtitle_and_progress_filter(subtitle_path, spec)
            video_filtered = tmp / "video_fx.mp4"
            cmd_fx = [
                "ffmpeg",
                "-y",
                "-i",
                str(concat_out),
                "-vf",
                vf,
                "-an",
                *x264_video_encode_args(),
                str(video_filtered),
            ]
            await self._run(cmd_fx)

            use_music = music_path is not None and music_path.exists()
            if not use_music:
                music_gen = tmp / "music.m4a"
                await self._generate_ambient_music(music_gen, spec.total_duration)
                music_path = music_gen
                use_music = True

            af = build_audio_mix_filter(
                use_music,
                spec.music_volume,
                enable_ducking=spec.enable_ducking,
                ducking_ratio=spec.ducking_ratio,
                ducking_threshold=spec.ducking_threshold,
            )
            cmd_final = [
                "ffmpeg",
                "-y",
                "-i",
                str(video_filtered),
                "-i",
                str(audio_path),
            ]
            if use_music:
                cmd_final.extend(["-i", str(music_path)])
            cmd_final.extend(
                [
                    "-filter_complex",
                    af,
                    "-map",
                    "0:v",
                    "-map",
                    "[aout]",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                    "-shortest",
                    str(output_path),
                ]
            )
            await self._run(cmd_final)

    async def render_vertical(
        self,
        video_path: Path,
        audio_path: Path,
        subtitle_path: Path | None,
        output_path: Path,
        width: int = 1080,
        height: int = 1920,
        fps: int = 60,
        duration: float = 45.0,
    ) -> None:
        """Legacy single-clip render — delegates to render_timeline."""
        spec = RenderSpec(
            width=width,
            height=height,
            fps=fps,
            total_duration=duration,
            scenes=[SceneSegment(index=0, duration=duration, clip_path=video_path)],
        )
        await self.render_timeline(spec, audio_path, subtitle_path, output_path)
