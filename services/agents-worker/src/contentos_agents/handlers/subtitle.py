"""Subtitle Agent — Subtitle Provider transcription + SRT/JSON export."""

import json
import re
import time

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta, AssetRef


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _segments_to_srt(segments: list[dict]) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        start = seg.get("start", 0)
        end = seg.get("end", start + 2)
        text = seg.get("text", "").strip()
        words = text.split()
        display = " ".join(f"<b>{w}</b>" if j == len(words) // 2 else w for j, w in enumerate(words))
        lines.extend([str(i), f"{_format_srt_time(start)} --> {_format_srt_time(end)}", display, ""])
    return "\n".join(lines)


class SubtitleAgentHandler(BaseAgentHandler):
    step = "subtitle"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        logs = ["Generating subtitles"]
        am = self.get_asset_manager()

        audio_ref_data = task_input.payload.get("audio_ref", {})
        audio_bytes = b""
        if audio_ref_data.get("key"):
            ref = AssetRef(
                id=task_input.job_id,
                category=AssetCategory.AUDIO,
                key=audio_ref_data["key"],
                bucket=audio_ref_data.get("bucket", "contentos"),
                content_type="audio/mpeg",
            )
            audio_bytes = await am.get(ref)

        subtitle = self.get_subtitle_provider()
        script = task_input.payload.get("script", {})
        duration_seconds = float(script.get("duration_seconds", 45))
        started = time.perf_counter()
        if audio_bytes:
            transcription = await subtitle.transcribe(audio_bytes)
            segments = transcription.get("segments", [])
            if segments:
                duration_seconds = float(segments[-1].get("end", duration_seconds))
        else:
            text = script.get("full_text", "")
            parts = re.split(r"(?<=[.!?])\s+", text)
            seg_dur = duration_seconds / max(len(parts), 1)
            segments = [{"start": i * seg_dur, "end": (i + 1) * seg_dur, "text": p} for i, p in enumerate(parts) if p]
        duration_ms = int((time.perf_counter() - started) * 1000)

        self._record_subtitle_cost(
            task_input,
            audio_bytes=len(audio_bytes),
            segment_count=len(segments),
            duration_ms=duration_ms,
            duration_seconds=duration_seconds,
            provider=getattr(subtitle, "provider_key", None) or getattr(subtitle, "name", None),
            model=getattr(subtitle, "model", None),
        )

        srt_content = _segments_to_srt(segments)
        srt_ref = await am.store(
            AssetCategory.CAPTIONS,
            srt_content.encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="subtitles.srt",
                content_type="text/plain",
            ),
        )
        json_ref = await am.store(
            AssetCategory.CAPTIONS,
            json.dumps({"segments": segments}).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="captions.json",
                content_type="application/json",
            ),
        )
        logs.append(f"{len(segments)} segments exported")
        logs.append(f"Cost tracked ({duration_ms}ms)")

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[srt_ref, json_ref],
            data={
                "subtitle_ref": {"key": srt_ref.key, "bucket": srt_ref.bucket},
                "captions_json_ref": {"key": json_ref.key, "bucket": json_ref.bucket},
                "segments": segments,
            },
            logs=logs,
        )
