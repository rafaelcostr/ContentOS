"""Quality Agent - validates render output with 0-10 technical score."""

import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.audiovisual_qa import check_subtitle_sync
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.providers.ffmpeg_provider import FFmpegProvider
from contentos_shared.quality_scoring import build_quality_report
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta, AssetRef


def _production_env() -> bool:
    value = os.getenv("APP_ENV") or os.getenv("ENV") or os.getenv("ENVIRONMENT")
    return str(value or "").strip().lower() in {"prod", "production", "release"}


def _require_real_media() -> bool:
    raw = os.getenv("QUALITY_REQUIRE_REAL_MEDIA") or os.getenv("EDITOR_REQUIRE_REAL_MEDIA")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return _production_env()


class QualityAgentHandler(BaseAgentHandler):
    step = "quality"

    REQUIRED_WIDTH = 1080
    REQUIRED_HEIGHT = 1920
    REQUIRED_FPS = 60
    MAX_DURATION = 60.0

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        logs = ["Running quality checks (1080x1920, H264, 60fps, sync) + scoring 0-10"]
        am = self.get_asset_manager()
        ffmpeg = FFmpegProvider()

        render = task_input.payload.get("render_ref", {})
        audio = task_input.payload.get("audio_ref", {})
        segments = task_input.payload.get("segments", [])
        subtitle_ref = task_input.payload.get("subtitle_ref", {})
        captions_ref = task_input.payload.get("captions_json_ref", {})
        render_diagnostics = task_input.payload.get("render_diagnostics") or {}
        require_real_media = _require_real_media()

        subtitle_sync_ok: bool | None = None
        bit_rate: int | None = None

        has_subtitle_artifacts = bool(subtitle_ref.get("key") or captions_ref.get("key"))
        has_segments = bool(segments)
        subtitle_sync_skipped = not has_segments and has_subtitle_artifacts
        if subtitle_sync_skipped:
            logs.append("Subtitle files present without segment list - sync check skipped")

        probe_state = {
            "has_render": bool(render.get("key")),
            "render_exists": False,
            "render_size_ok": False,
            "has_audio_ref": bool(audio.get("key")),
            "has_audio_stream": False,
            "has_subtitles": has_segments or has_subtitle_artifacts,
            "subtitle_sync_skipped": subtitle_sync_skipped,
            "width": 0,
            "height": 0,
            "codec": "",
            "fps": 0.0,
            "duration": 0.0,
            "extra_errors": [],
        }
        self._apply_render_diagnostics(probe_state, render_diagnostics, require_real_media)

        if render.get("key"):
            ref = AssetRef(
                id=uuid4(),
                category=AssetCategory.RENDERS,
                key=render["key"],
                bucket=render.get("bucket", "contentos"),
                content_type="video/mp4",
            )
            probe_state["render_exists"] = await am.exists(ref)
            if probe_state["render_exists"]:
                meta = await am.get_metadata(ref)
                probe_state["render_size_ok"] = meta.get("size", 0) >= 10_000

                with tempfile.TemporaryDirectory() as tmp:
                    video_path = Path(tmp) / "check.mp4"
                    video_path.write_bytes(await am.get(ref))
                    if video_path.stat().st_size < 10_000:
                        probe_state["render_size_ok"] = False
                    else:
                        probe = await ffmpeg.probe(video_path)
                        streams = probe.get("streams", [])
                        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
                        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

                        probe_state["has_audio_stream"] = audio_stream is not None
                        probe_state["duration"] = float(probe.get("format", {}).get("duration", 0))

                        if video_stream:
                            probe_state["width"] = int(video_stream.get("width", 0))
                            probe_state["height"] = int(video_stream.get("height", 0))
                            probe_state["codec"] = str(video_stream.get("codec_name", ""))
                            fps_str = video_stream.get("r_frame_rate", "0/1")
                            try:
                                num, den = map(int, fps_str.split("/"))
                                probe_state["fps"] = num / den if den else 0.0
                            except (ValueError, ZeroDivisionError):
                                probe_state["fps"] = 0.0
                            logs.append(
                                f"Probe: {probe_state['width']}x{probe_state['height']} "
                                f"{probe_state['duration']:.1f}s {probe_state['fps']:.1f}fps"
                            )

                        fmt_bitrate = probe.get("format", {}).get("bit_rate")
                        if fmt_bitrate is not None:
                            try:
                                bit_rate = int(fmt_bitrate)
                            except (TypeError, ValueError):
                                bit_rate = None

        if has_segments and subtitle_ref.get("key"):
            srt_ref = AssetRef(
                id=uuid4(),
                category=AssetCategory.CAPTIONS,
                key=subtitle_ref["key"],
                bucket=subtitle_ref.get("bucket", "contentos"),
                content_type="text/plain",
            )
            if await am.exists(srt_ref):
                srt_text = (await am.get(srt_ref)).decode("utf-8", errors="replace")
                subtitle_sync_ok, sync_detail = check_subtitle_sync(segments, srt_text)
                logs.append(f"Subtitle sync: {sync_detail}")
                if not subtitle_sync_ok:
                    probe_state["extra_errors"].append(f"Subtitle sync failed: {sync_detail}")

        report = build_quality_report(
            **probe_state,
            subtitle_sync_ok=subtitle_sync_ok,
            bit_rate=bit_rate,
        )
        logs.append(f"Quality score: {report.score}/10 (min={report.min_score}) passed={report.passed}")
        for name, value in report.dimensions.items():
            logs.append(f"  {name}: {value}/10")

        report_payload = report.to_dict()
        ref = await am.store(
            AssetCategory.ASSETS,
            json.dumps(report_payload, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="quality_report.json",
                content_type="application/json",
            ),
        )

        if not report.passed:
            logs.extend([f"FAIL: {e}" for e in report.errors])
            if report.suggestions:
                logs.append("Suggestions: " + "; ".join(report.suggestions[:3]))
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.FAILED.value,
                artifacts=[ref],
                data={
                    **report_payload,
                    "retry_step": "editor",
                },
                logs=logs,
                error="; ".join(report.errors) or f"Quality score {report.score} below {report.min_score}",
            )

        logs.append("All quality checks passed")
        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data=report_payload,
            logs=logs,
        )

    def _apply_render_diagnostics(self, probe_state: dict, diagnostics: dict, require_real_media: bool) -> None:
        if not diagnostics:
            return
        missing_clip_count = int(diagnostics.get("missing_clip_count") or 0)
        used_silent_audio = bool(diagnostics.get("used_silent_audio"))
        subtitles_embedded = bool(diagnostics.get("subtitles_embedded"))

        probe_state["has_real_clips"] = missing_clip_count == 0
        probe_state["missing_clip_count"] = missing_clip_count
        probe_state["has_narration_audio"] = not used_silent_audio

        if require_real_media and missing_clip_count:
            labels = diagnostics.get("placeholder_scene_labels") or []
            probe_state["extra_errors"].append(
                "Render contains placeholder scenes"
                + (": " + ", ".join(str(label) for label in labels) if labels else "")
            )
        if require_real_media and used_silent_audio:
            probe_state["extra_errors"].append("Render used generated/silent narration audio")
        if require_real_media and not subtitles_embedded:
            probe_state["extra_errors"].append("Render was produced without embedded subtitles")
