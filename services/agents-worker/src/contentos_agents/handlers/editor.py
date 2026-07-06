"""Video Editor Agent — FFmpeg timeline assembly 1080x1920 60fps."""

import os
import tempfile
from pathlib import Path
from uuid import uuid4

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.director_plan import directive_for_index
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.providers.ffmpeg_filters import RenderSpec, SceneSegment
from contentos_shared.providers.ffmpeg_provider import FFmpegProvider
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta, AssetRef


class EditorAgentHandler(BaseAgentHandler):
    step = "editor"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        logs = ["Starting timeline render (1080x1920 @ 60fps)"]
        am = self.get_asset_manager()
        ffmpeg = FFmpegProvider()

        script = task_input.payload.get("script", {})
        scenes = task_input.payload.get("scenes", [])
        clips = task_input.payload.get("clips", [])
        total_duration = float(script.get("duration_seconds", 45))
        total_duration = min(max(total_duration, 10), 60)

        audio_data = task_input.payload.get("audio_ref", {})
        subtitle_data = task_input.payload.get("subtitle_ref", {})

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            audio_path = tmp_path / "narration.mp3"
            if audio_data.get("key"):
                audio_ref = AssetRef(
                    id=uuid4(),
                    category=AssetCategory.AUDIO,
                    key=audio_data["key"],
                    bucket=audio_data.get("bucket", "contentos"),
                    content_type="audio/mpeg",
                )
                audio_path.write_bytes(await am.get(audio_ref))
                logs.append("Narration loaded")
            else:
                logs.append("No audio — generating silent track")
                await ffmpeg._generate_ambient_music(audio_path, total_duration)

            srt_path: Path | None = None
            if subtitle_data.get("key"):
                srt_ref = AssetRef(
                    id=uuid4(),
                    category=AssetCategory.CAPTIONS,
                    key=subtitle_data["key"],
                    bucket=subtitle_data.get("bucket", "contentos"),
                    content_type="text/plain",
                )
                srt_path = tmp_path / "subs.srt"
                srt_path.write_bytes(await am.get(srt_ref))
                logs.append("Subtitles loaded")

            director_plan = task_input.payload.get("director_plan")
            default_fade = float(
                (director_plan or {}).get("default_fade") or os.getenv("EDITOR_FADE_DURATION", "0.4")
            )

            scene_segments = await self._build_scene_segments(
                tmp_path, scenes, clips, total_duration, am, logs, director_plan
            )

            music_path = await self._resolve_music(tmp_path, am, logs)

            spec = RenderSpec(
                width=1080,
                height=1920,
                fps=60,
                total_duration=total_duration,
                scenes=scene_segments,
                enable_zoom=os.getenv("EDITOR_ENABLE_ZOOM", "true").lower() == "true",
                fade_duration=default_fade,
                music_volume=float(os.getenv("EDITOR_MUSIC_VOLUME", "0.12")),
            )

            output_path = tmp_path / "render.mp4"
            await ffmpeg.render_timeline(
                spec=spec,
                audio_path=audio_path,
                subtitle_path=srt_path,
                output_path=output_path,
                music_path=music_path,
            )

            probe = await ffmpeg.probe(output_path)
            render_bytes = output_path.read_bytes()
            duration = float(probe.get("format", {}).get("duration", total_duration))
            logs.append(f"Render complete: {len(render_bytes)} bytes, {duration:.1f}s")

        render_ref = await am.store(
            AssetCategory.RENDERS,
            render_bytes,
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="final.mp4",
                content_type="video/mp4",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[render_ref],
            data={
                "render_ref": {
                    "key": render_ref.key,
                    "bucket": render_ref.bucket,
                    "id": str(render_ref.id),
                },
                "width": 1080,
                "height": 1920,
                "fps": 60,
                "duration_seconds": duration,
                "scene_count": len(scene_segments),
                "segments": task_input.payload.get("segments", []),
                "audio_ref": audio_data if audio_data.get("key") else task_input.payload.get("audio_ref", {}),
                "subtitle_ref": subtitle_data if subtitle_data.get("key") else task_input.payload.get("subtitle_ref", {}),
            },
            logs=logs,
        )

    async def _build_scene_segments(
        self,
        tmp_path: Path,
        scenes: list[dict],
        clips: list[dict],
        total_duration: float,
        am,
        logs: list[str],
        director_plan: dict | None = None,
    ) -> list[SceneSegment]:
        if not scenes:
            return [SceneSegment(index=0, duration=total_duration, label="main")]

        segments: list[SceneSegment] = []
        if director_plan:
            logs.append(f"Director plan: pacing={director_plan.get('pacing', 'medium')}")

        for i, scene in enumerate(scenes):
            directive = directive_for_index(director_plan, i)
            start = float(scene.get("start_seconds", i * 5))
            end = float(scene.get("end_seconds", start + 5))
            duration = max(end - start, 1.0)
            if directive and directive.get("duration_seconds"):
                duration = max(float(directive["duration_seconds"]), 1.0)

            clip_path: Path | None = None
            clip_data = clips[i] if i < len(clips) else (clips[0] if clips else None)
            if clip_data and clip_data.get("asset_key"):
                local = tmp_path / f"clip_{i}.mp4"
                ref = AssetRef(
                    id=uuid4(),
                    category=AssetCategory.TAKES,
                    key=clip_data["asset_key"],
                    bucket=clip_data.get("bucket", "contentos"),
                    content_type="video/mp4",
                )
                try:
                    local.write_bytes(await am.get(ref))
                    clip_path = local
                except Exception:
                    logs.append(f"Clip {i} unavailable — placeholder")

            segment = SceneSegment(
                index=i,
                duration=duration,
                clip_path=clip_path,
                label=scene.get("label", f"scene_{i}"),
            )
            if directive:
                if "zoom_enabled" in directive:
                    segment.zoom_enabled = bool(directive["zoom_enabled"])
                if directive.get("zoom_max") is not None:
                    segment.zoom_max = float(directive["zoom_max"])
                if directive.get("zoom_rate") is not None:
                    segment.zoom_rate = float(directive["zoom_rate"])
                if directive.get("pan_x_expr"):
                    segment.pan_x_expr = str(directive["pan_x_expr"])
                if directive.get("fade_in") is not None:
                    segment.fade_in = float(directive["fade_in"])
                if directive.get("fade_out") is not None:
                    segment.fade_out = float(directive["fade_out"])
                if directive.get("crop_bias"):
                    segment.crop_bias = str(directive["crop_bias"])

            segments.append(segment)

        logs.append(f"Timeline: {len(segments)} scenes")
        return segments

    async def _resolve_music(self, tmp_path: Path, am, logs: list[str]) -> Path | None:
        """Optional background music from assets/music/ in MinIO."""
        music_key = os.getenv("EDITOR_MUSIC_KEY", "assets/music/ambient.mp3")
        ref = AssetRef(
            id=uuid4(),
            category=AssetCategory.AUDIO,
            key=music_key,
            bucket=os.getenv("MINIO_BUCKET", "contentos"),
            content_type="audio/mpeg",
        )
        if await am.exists(ref):
            path = tmp_path / "music.mp3"
            path.write_bytes(await am.get(ref))
            logs.append("Custom background music loaded")
            return path
        logs.append("Using generated ambient music")
        return None
