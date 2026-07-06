"""Voice Agent — Speech Provider narration."""

import time

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta


class VoiceAgentHandler(BaseAgentHandler):
    step = "voice"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        script = task_input.payload.get("script", {})
        full_text = script.get("full_text", "")
        logs = [f"generating voice ({len(full_text)} chars)"]

        provider = self.get_speech_provider()
        started = time.perf_counter()
        audio_bytes = await provider.text_to_speech(full_text)
        duration_ms = int((time.perf_counter() - started) * 1000)

        self._record_speech_cost(
            task_input,
            text=full_text,
            audio_bytes=len(audio_bytes),
            duration_ms=duration_ms,
            provider=getattr(provider, "provider_key", None) or getattr(provider, "name", None),
            model=getattr(provider, "model", None),
        )

        ref = await self.get_asset_manager().store(
            AssetCategory.AUDIO,
            audio_bytes,
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="narration.mp3",
                content_type="audio/mpeg",
            ),
        )
        logs.append(f"Audio stored: {ref.key}")
        logs.append(f"Cost tracked ({duration_ms}ms)")

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={"audio_ref": {"key": ref.key, "bucket": ref.bucket, "id": str(ref.id)}},
            logs=logs,
        )
