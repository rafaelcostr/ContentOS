"""Asset Index Agent — tag and index collected assets (V2 pipeline step)."""

from contentos_agents.handlers._storage import agent_storage_settings
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_storage.application.asset_pipeline_service import AssetPipelineService
from contentos_storage.factory import get_asset_manager


class AssetIndexAgentHandler(BaseAgentHandler):
    step = "asset_index"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        collected = task_input.payload.get("assets", [])
        asset_ids = [a.get("asset_id") for a in collected if a.get("asset_id")]
        logs = [f"[asset_index] indexing {len(asset_ids)} assets"]

        pipeline = AssetPipelineService(get_asset_manager(agent_storage_settings()))
        indexed = pipeline.index_assets_sync(asset_ids, task_input.pipeline_id)
        logs.append(f"Tagged {indexed} assets in database")

        if asset_ids and indexed == 0:
            logs.append("WARN: no Asset rows found — check asset_collector persistence")

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            data={"indexed_count": indexed, "asset_ids": asset_ids},
            logs=logs,
        )
