"""Media Analyze Agent — vision tags + embeddings for collected video assets (V5.0.3)."""

import os

from contentos_agents.handlers._storage import agent_storage_settings
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_storage.application.media_analyze_service import MediaAnalyzeService
from contentos_storage.factory import get_asset_manager


class MediaAnalyzeAgentHandler(BaseAgentHandler):
    step = "media_analyze"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        if os.getenv("ENABLE_MEDIA_ANALYZE", "true").lower() not in ("1", "true", "yes"):
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                data={"analyzed_count": 0, "skipped": True},
                logs=["[media_analyze] disabled via ENABLE_MEDIA_ANALYZE"],
            )

        asset_ids = list(task_input.payload.get("asset_ids") or [])
        if not asset_ids:
            collected = task_input.payload.get("assets") or []
            asset_ids = [a.get("asset_id") for a in collected if a.get("asset_id")]

        topic = task_input.payload.get("topic") or task_input.payload.get("script", {}).get("title", "")
        logs = [f"[media_analyze] analyzing {len(asset_ids)} assets"]

        if not asset_ids:
            logs.append("No assets to analyze — skipping")
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                data={"analyzed_count": 0, "results": []},
                logs=logs,
            )

        vision_prompt = None
        try:
            prompt = self.render_prompt(
                "media_analyze",
                {"topic": topic, "asset_count": str(len(asset_ids))},
                project_id=task_input.project_id,
            )
            logs.append(f"Prompt v{prompt.version}")
            vision_prompt = prompt.user
        except Exception as exc:
            logs.append(f"Prompt render skipped: {exc}")

        service = MediaAnalyzeService(
            get_asset_manager(agent_storage_settings()),
            database_url=os.getenv("DATABASE_URL"),
        )
        results = await service.analyze_asset_ids(
            asset_ids,
            pipeline_id=task_input.pipeline_id,
            project_id=task_input.project_id,
            topic=topic,
            vision_prompt=vision_prompt,
        )
        analyzed = sum(1 for r in results if r.analyzed)
        skipped = sum(1 for r in results if r.skipped)
        logs.append(f"Analyzed {analyzed}, skipped {skipped}")

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            data={
                "analyzed_count": analyzed,
                "skipped_count": skipped,
                "results": [r.__dict__ for r in results],
                "asset_ids": asset_ids,
            },
            logs=logs,
        )
