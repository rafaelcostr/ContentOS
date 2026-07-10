"""Video Editor Agent — FFmpeg timeline assembly 1080x1920 60fps."""

import os
import tempfile
from pathlib import Path
from uuid import uuid4

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.cinematic import CinematicSettings, apply_directive_to_segment
from contentos_shared.director_plan import directive_for_index
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.media_production import render_allow_placeholder
from contentos_shared.providers.ffmpeg_filters import RenderSpec, SceneSegment
from contentos_shared.providers.ffmpeg_provider import FFmpegProvider
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta, AssetRef
from contentos_storage.application.asset_pipeline_service import AssetPipelineService


class EditorAgentHandler(BaseAgentHandler):
    step = "editor"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        logs = ["Starting timeline render (1080x1920 @ 60fps)"]
        am = self.get_asset_manager()
        ffmpeg = FFmpegProvider()

        script = task_input.payload.get("script", {})
        scenes = task_input.payload.get("scenes", [])
        clips = task_input.payload.get("clips", [])
        min_duration = float(os.getenv("MIN_VIDEO_DURATION_SECONDS", "30"))
        total_duration = float(script.get("duration_seconds", 45))
        total_duration = min(max(total_duration, min_duration), 60)

        audio_data = task_input.payload.get("audio_ref", {})
        subtitle_data = task_input.payload.get("subtitle_ref", {})
        used_silent_audio = not bool(audio_data.get("key"))

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
            cinematic = CinematicSettings.from_payload(task_input.payload)
            default_fade = float(
                cinematic.fade_duration
                or (director_plan or {}).get("default_fade")
                or os.getenv("EDITOR_FADE_DURATION", "0.4")
            )

            scene_segments = await self._build_scene_segments(
                tmp_path,
                scenes,
                clips,
                total_duration,
                am,
                logs,
                director_plan,
                cinematic,
            )
            actual_duration = sum(segment.duration for segment in scene_segments)
            if scene_segments and actual_duration < min_duration:
                extra = min_duration - actual_duration
                scene_segments[-1].duration += extra
                logs.append(f"Extended final scene by {extra:.1f}s to respect minimum duration")
            total_duration = max(total_duration, sum(segment.duration for segment in scene_segments))

            placeholder_scene_labels = [segment.label for segment in scene_segments if segment.clip_path is None]
            real_clip_count = len(scene_segments) - len(placeholder_scene_labels)
            if placeholder_scene_labels:
                logs.append("Placeholder scenes: " + ", ".join(placeholder_scene_labels))
            if placeholder_scene_labels and not render_allow_placeholder():
                return AgentTaskOutput(
                    job_id=task_input.job_id,
                    status=JobStatus.FAILED.value,
                    error=(
                        "placeholder render blocked in production: "
                        + ", ".join(placeholder_scene_labels)
                    ),
                    data={
                        "render_diagnostics": {
                            "placeholder_scene_labels": placeholder_scene_labels,
                            "real_clip_count": real_clip_count,
                            "scene_count": len(scene_segments),
                        }
                    },
                    logs=logs,
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
            cinematic.apply_to_render_spec(spec)
            logs.append(
                f"Cinematic preset={cinematic.preset} "
                f"zoom={cinematic.enable_zoom} ducking={cinematic.enable_ducking} "
                f"speed_ramp={cinematic.enable_speed_ramp}"
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

        persisted = await AssetPipelineService(am).store_and_persist(
            AssetCategory.RENDERS,
            render_bytes,
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="final.mp4",
                content_type="video/mp4",
            ),
            extra_tags=["render", "final", f"pipeline:{task_input.pipeline_id}"],
            metadata={
                "topic": task_input.payload.get("topic") or script.get("title"),
                "duration_seconds": duration,
                "width": 1080,
                "height": 1920,
                "fps": 60,
                "scene_count": len(scene_segments),
            },
        )
        render_ref = persisted.ref
        if persisted.deduplicated:
            logs.append(f"Render deduplicated: {render_ref.key}")
        else:
            logs.append(f"Render indexed: {render_ref.key}")

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
                "render_diagnostics": {
                    "used_silent_audio": used_silent_audio,
                    "subtitles_embedded": bool(srt_path),
                    "placeholder_scene_labels": placeholder_scene_labels,
                    "missing_clip_count": len(placeholder_scene_labels),
                    "real_clip_count": real_clip_count,
                    "scene_count": len(scene_segments),
                    "has_custom_music": bool(music_path),
                },
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
        cinematic: CinematicSettings | None = None,
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
                apply_directive_to_segment(segment, directive)
                if cinematic and not cinematic.enable_speed_ramp:
                    segment.playback_speed = 1.0
                    segment.speed_ramp_end = None

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
