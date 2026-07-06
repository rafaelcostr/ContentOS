"""Research Agent handler."""

import json

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import normalize_research_output
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta


class ResearchAgentHandler(BaseAgentHandler):
    step = "research"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        topic = task_input.payload.get("topic", "")
        logs = [f"Researching: {topic}"]

        prompt = self.render_prompt(
            "research",
            {
                "topic": topic,
                "niche": task_input.payload.get("niche", ""),
                "trend_context": task_input.payload.get("trend_context", ""),
            },
            project_id=task_input.project_id,
        )
        logs.append(f"Prompt v{prompt.version}")

        data, from_cache, cache_key = await self.chat_json_with_cache(
            prompt,
            topic=topic,
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            job_id=task_input.job_id,
        )
        if from_cache:
            logs.append(f"Cache hit ({cache_key})")
        data = normalize_research_output(data)
        logs.append(f"Found {len(data.get('topics', []))} topics")

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(data).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="research.json",
                content_type="application/json",
            ),
        )
        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data=data,
            logs=logs,
        )
