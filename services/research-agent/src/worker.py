"""Research Agent — discovers viral topics."""

import json
import os
from uuid import UUID

from contentos_shared.agents.base import BaseAgentHandler, run_async
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta
from contentos_workflow.tasks import celery_app


class ResearchAgentHandler(BaseAgentHandler):
    step = "research"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        topic = task_input.payload.get("topic", "")
        logs = [f"Researching: {topic}"]

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "Research viral short-form video topics. Return JSON with topics[] and selected_topic.",
                },
                {"role": "user", "content": f"Research viral angles for: {topic}"},
            ],
        )
        data = json.loads(response.choices[0].message.content or "{}")
        logs.append(f"Found {len(data.get('topics', []))} topics")

        asset_manager = self.get_asset_manager()
        ref = await asset_manager.store(
            AssetCategory.SCRIPTS,
            json.dumps(data).encode(),
            AssetMeta(
                project_id=UUID(str(task_input.project_id)),
                pipeline_id=UUID(str(task_input.pipeline_id)),
                filename="research.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=UUID(str(task_input.job_id)),
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data=data,
            logs=logs,
        )


handler = ResearchAgentHandler()


@celery_app.task(name="contentos.research.execute", bind=True, max_retries=0)
def execute(self, **kwargs):
    return run_async(handler.run(**kwargs))
