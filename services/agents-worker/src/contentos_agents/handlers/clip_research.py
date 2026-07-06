"""Clip Research Agent — search content sources per scene (V2 async)."""

import json

from contentos_agents.handlers._pipeline_base import PipelineAwareHandler
from contentos_shared.enums import JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput

try:
    from contentos_sources import get_collection_store, get_source_manager
except ImportError:

    def get_source_manager():  # type: ignore[misc]
        return None

    def get_collection_store():  # type: ignore[misc]
        return None


class ClipResearchAgentHandler(PipelineAwareHandler):
    step = "clip_research"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        scenes = task_input.payload.get("scenes", [])
        topic = task_input.payload.get("topic") or task_input.payload.get("script", {}).get("title", "")
        logs = [f"[clip_research] {len(scenes)} scenes for pipeline {task_input.pipeline_id}"]

        mgr = get_source_manager()
        if not mgr:
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.FAILED.value,
                error="content-sources package not available",
                logs=logs,
            )

        scene_results = await mgr.search_all_scenes(scenes, task_input.project_id, topic)
        logs.append(f"Found candidates across {len(mgr.list_sources())} sources")

        try:
            prompt = self.render_prompt(
                "clip_research",
                {
                    "topic": topic,
                    "scenes_json": json.dumps(scenes, ensure_ascii=False)[:4000],
                },
                project_id=task_input.project_id,
            )
            logs.append(f"Prompt v{prompt.version}")
            refined, from_cache, cache_key = await self.chat_json_with_cache(
                prompt,
                topic=topic,
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                job_id=task_input.job_id,
            )
            if from_cache:
                logs.append(f"Cache hit ({cache_key})")
            if refined.get("queries"):
                logs.append(f"LLM refined {len(refined['queries'])} scene queries")
        except Exception as exc:
            logs.append(f"LLM refine skipped: {exc}")

        store = get_collection_store()
        if store:
            store.save_candidates(task_input.pipeline_id, task_input.project_id, scene_results)

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            data={"scene_candidates": scene_results, "sources": mgr.list_sources()},
            logs=logs,
        )

    async def _on_async_complete(self, output: AgentTaskOutput) -> None:
        if output.status != JobStatus.COMPLETED.value or not self._async_mode:
            return
        try:
            from contentos_workflow.tasks import dispatch_async_agent

            ti = self._last_task_input
            payload = dict(ti.payload)
            payload["scene_candidates"] = output.data.get("scene_candidates", [])
            dispatch_async_agent("asset_collector", str(ti.pipeline_id), str(ti.project_id), payload)
        except Exception:
            pass
