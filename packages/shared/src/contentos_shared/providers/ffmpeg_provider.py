"""FFmpeg video assembly — 1080x1920 vertical shorts with effects."""

import asyncio
import json
import os
import tempfile
from pathlib import Path

from contentos_shared.providers.ffmpeg_filters import (
    RenderSpec,
    SceneSegment,
    build_audio_mix_filter,
    placeholder_video_filter,
    scene_video_filter,
    subtitle_and_progress_filter,
)


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
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                str(video_filtered),
            ]
            await self._run(cmd_fx)

            use_music = music_path is not None and music_path.exists()
            if not use_music:
                music_gen = tmp / "music.m4a"
                await self._generate_ambient_music(music_gen, spec.total_duration)
                music_path = music_gen
                use_music = True

            af = build_audio_mix_filter(use_music, spec.music_volume)
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
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-r",
                    str(spec.fps),
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
