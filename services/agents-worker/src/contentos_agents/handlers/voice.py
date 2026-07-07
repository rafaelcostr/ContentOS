"""Voice Agent — Speech Provider narration with voice profiles (V5.1.1)."""

from __future__ import annotations

import time

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta
from contentos_shared.voice.narration import (
    build_profiled_speech_provider,
    resolve_voice_profile,
    synthesize_narration,
)


class VoiceAgentHandler(BaseAgentHandler):
    step = "voice"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        script = task_input.payload.get("script", {})
        full_text = script.get("full_text", "")
        profile = resolve_voice_profile(task_input.payload, task_input.project_id)
        logs = [
            f"generating voice ({len(full_text)} chars)",
            f"profile={profile.name} speed={profile.speed} pitch={profile.pitch_semitones} pause={profile.pause_ms}ms",
        ]

        provider = build_profiled_speech_provider(profile, agent=self.step)
        started = time.perf_counter()
        audio_bytes = await synthesize_narration(provider, full_text, profile)
        duration_ms = int((time.perf_counter() - started) * 1000)

        self._record_speech_cost(
            task_input,
            text=full_text,
            audio_bytes=len(audio_bytes),
            duration_ms=duration_ms,
            provider=getattr(provider, "provider_key", None) or profile.provider,
            model=profile.voice_id or getattr(provider, "model", None),
        )

        ref = await self.get_asset_manager().store(
            AssetCategory.AUDIO,
            audio_bytes,
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="narration.mp3",
                content_type="audio/mpeg",
                tags={
                    "voice_profile": profile.name,
                    "speed": str(profile.speed),
                    "pitch": str(profile.pitch_semitones),
                },
            ),
        )
        logs.append(f"Audio stored: {ref.key}")
        logs.append(f"Cost tracked ({duration_ms}ms)")

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "audio_ref": {"key": ref.key, "bucket": ref.bucket, "id": str(ref.id)},
                "voice_profile": profile.to_dict(),
            },
            logs=logs,
        )
