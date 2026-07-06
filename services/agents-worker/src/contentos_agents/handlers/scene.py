"""Scene Planner Agent — splits script into timed scenes."""

import json

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta


class SceneAgentHandler(BaseAgentHandler):
    step = "scene"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        script = coerce_dict(task_input.payload.get("script"))
        topic = script.get("title") or task_input.payload.get("topic", "untitled")
        logs = ["Planning scenes"]

        prompt = self.render_prompt(
            "scene",
            {"script_json": json.dumps(script, ensure_ascii=False)},
            project_id=task_input.project_id,
        )
        logs.append(f"Prompt v{prompt.version}")
        result, from_cache, cache_key = await self.chat_json_with_cache(
            prompt,
            topic=topic,
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            job_id=task_input.job_id,
        )
        if from_cache:
            logs.append(f"Cache hit ({cache_key})")
        scenes = result.get("scenes", [])
        logs.append(f"Created {len(scenes)} scenes")

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps({"scenes": scenes}).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="scenes.json",
                content_type="application/json",
            ),
        )
        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={"scenes": scenes, "script": script},
            logs=logs,
        )
