"""Publisher Agent — metadata + platform plugins (TikTok, YouTube, Instagram)."""

import json
import os

from contentos_database.publish_credentials import load_merged_project_credentials
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.plugins.context import PublishContext
from contentos_shared.plugins.loader import ensure_plugins_loaded, run_post_publish
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta


class PublisherAgentHandler(BaseAgentHandler):
    step = "publisher"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        ensure_plugins_loaded()
        script = task_input.payload.get("script", {})
        topic = task_input.payload.get("topic") or script.get("title", "")
        logs = [f"Preparing publication for: {topic}"]

        prompt = self.render_prompt(
            "publisher",
            {"topic": topic, "script_json": json.dumps(script, ensure_ascii=False)},
            project_id=task_input.project_id,
        )
        logs.append(f"Prompt v{prompt.version}")
        base_metadata, from_cache, cache_key = await self.chat_json_with_cache(
            prompt,
            topic=topic,
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            job_id=task_input.job_id,
        )
        if from_cache:
            logs.append(f"Cache hit ({cache_key})")

        credentials = self._load_credentials_from_env()
        credentials = await load_merged_project_credentials(task_input.project_id, credentials)
        context = PublishContext(
            pipeline_id=task_input.pipeline_id,
            project_id=task_input.project_id,
            topic=topic,
            script=script,
            base_metadata=base_metadata,
            render_ref=task_input.payload.get("render_ref"),
            credentials=credentials,
        )

        platform_publications = await run_post_publish(context)
        mode = os.getenv("PUBLISH_MODE", "dry_run")
        logs.append(f"Publish mode: {mode}")
        for platform, pub in platform_publications.items():
            logs.append(f"  {platform}: {pub.get('status')} — {pub.get('title', '')[:50]}")

        publication = {
            "title": base_metadata.get("title", topic),
            "description": base_metadata.get("description", ""),
            "hashtags": base_metadata.get("hashtags", []),
            "status": "ready",
            "mode": mode,
            "platforms": platform_publications,
        }

        ref = await self.get_asset_manager().store(
            AssetCategory.ASSETS,
            json.dumps(publication, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="publication.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={"publication": publication, "platform_publications": platform_publications},
            logs=logs,
        )

    def _load_credentials_from_env(self) -> dict[str, dict]:
        """Load channel credentials from env JSON (optional)."""
        raw = os.getenv("PLATFORM_CREDENTIALS_JSON", "{}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
