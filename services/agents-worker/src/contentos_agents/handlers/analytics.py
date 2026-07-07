"""Analytics AI Agent — async post-publication analysis (V2.8)."""

import json

from contentos_agents.handlers._pipeline_base import PipelineAwareHandler
from contentos_intelligence.application.performance_learning.pipeline_feedback import (
    build_pipeline_performance_feedback,
)
from contentos_shared.enums import JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput

try:
    from contentos_analytics_ai import get_analytics_service
except ImportError:

    def get_analytics_service():  # type: ignore[misc]
        return None


class AnalyticsAgentHandler(PipelineAwareHandler):
    step = "analytics"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        svc = get_analytics_service()
        payload = task_input.payload
        logs = [f"[analytics] Analyzing pipeline {task_input.pipeline_id}"]

        metrics = svc.collect_metrics(payload) if svc else {}
        performance_feedback = build_pipeline_performance_feedback({**payload, "metrics": metrics})
        models_used = svc.collect_models_used() if svc else {}
        prompts_used = svc.collect_prompts_used() if svc else {}
        publication = payload.get("publication") or {}

        prompt = self.render_prompt(
            "analytics",
            {
                "metrics_json": json.dumps(metrics, ensure_ascii=False),
                "publication_json": json.dumps(publication, ensure_ascii=False),
                "performance_feedback_json": json.dumps(performance_feedback, ensure_ascii=False),
            },
            project_id=task_input.project_id,
        )
        logs.append(f"Prompt v{prompt.version}")

        topic = payload.get("topic") or publication.get("title", "video")
        analysis, from_cache, cache_key = await self.chat_json_with_cache(
            prompt,
            topic=topic,
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            job_id=task_input.job_id,
        )
        if from_cache:
            logs.append(f"Cache hit ({cache_key})")

        applied = False
        if svc and svc.auto_apply_enabled():
            applied = svc.apply_to_memory(task_input.project_id, analysis, task_input.pipeline_id)
            if applied:
                logs.append("Applied suggestions to project memory")

        insight_data = None
        if svc:
            from contentos_analytics_ai.domain.insight import AnalyticsInsightData

            insight_data = AnalyticsInsightData(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                metrics={**metrics, "performance_feedback": performance_feedback},
                analysis=analysis,
                models_used=models_used,
                prompts_used=prompts_used,
                performance_feedback=performance_feedback,
                applied_to_memory=applied,
            )
            svc.save_insight(insight_data)
            logs.append(f"Insight saved (score={analysis.get('score', '—')})")

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            data={
                "metrics": metrics,
                "performance_feedback": performance_feedback,
                "analysis": analysis,
                "models_used": models_used,
                "prompts_used": prompts_used,
                "applied_to_memory": applied,
            },
            logs=logs,
        )
