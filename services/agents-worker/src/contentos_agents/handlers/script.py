"""Script Agent — creates 30-60s viral scripts."""

import json

from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta


class ScriptAgentHandler(BaseAgentHandler):
    step = "script"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        selected = coerce_dict(task_input.payload.get("selected_topic"))
        topic = selected.get("title") or task_input.payload.get("topic", "")
        logs = [f"Writing script for: {topic}"]

        hook = coerce_dict(task_input.payload.get("selected_hook") or task_input.payload.get("hook"))
        hook_text = task_input.payload.get("hook_text") or hook.get("hook_text") or ""
        hook_style = task_input.payload.get("hook_style") or hook.get("style") or ""
        if hook_text:
            logs.append(f"Using Hook Generator: [{hook_style}] {hook_text}")

        context = {
            **selected,
            "selected_hook": hook or None,
            "hook_text": hook_text,
            "hook_style": hook_style,
        }

        prompt = self.render_prompt(
            "script",
            {
                "topic": topic,
                "context": json.dumps(context, ensure_ascii=False),
                "hook_text": str(hook_text),
                "hook_style": str(hook_style),
            },
            project_id=task_input.project_id,
        )
        logs.append(f"Prompt v{prompt.version}")
        script, from_cache, cache_key = await self.chat_json_with_cache(
            prompt,
            topic=topic,
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            job_id=task_input.job_id,
        )
        if from_cache:
            logs.append(f"Cache hit ({cache_key})")
        script = coerce_dict(script, string_key="full_text") if not isinstance(script, dict) else script
        if hook_text and not script.get("hook"):
            script["hook"] = hook_text
        if hook_style:
            script["hook_style"] = hook_style
        logs.append(f"Script duration: {script.get('duration_seconds', 45)}s")

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(script).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="script.json",
                content_type="application/json",
            ),
        )
        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={"script": script},
            logs=logs,
        )
