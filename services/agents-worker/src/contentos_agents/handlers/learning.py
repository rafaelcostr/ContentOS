"""Learning Engine agent — post-pipeline memory + KB (V4.2.3 / Epic 7)."""

from __future__ import annotations

import json

from contentos_agents.handlers._pipeline_base import PipelineAwareHandler
from contentos_intelligence.application.learning import LearningEngine, is_learning_enabled
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta

try:
    from contentos_events import DomainEvent, get_event_bus
    from contentos_events.domain.event_types import LEARNING_RECORDED
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]
    LEARNING_RECORDED = "learning.recorded"  # type: ignore[misc]

    def get_event_bus():  # type: ignore[misc]
        return None


class LearningAgentHandler(PipelineAwareHandler):
    step = "learning"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        if not is_learning_enabled():
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                data={"learning_skipped": True},
                logs=["[learning] Disabled via LEARNING_ENGINE_ENABLED"],
            )

        topic = str(task_input.payload.get("topic") or "")
        logs = [f"[learning] Recording insights for pipeline {task_input.pipeline_id}"]

        context = IntelligenceContext(
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            topic=topic,
            payload=dict(task_input.payload),
        )
        report = LearningEngine().process(context)
        report_dict = report.to_dict()

        logs.append(f"Signals: {report_dict.get('signal_count', 0)}")
        if report.memory_applied:
            logs.append(f"Memory updated: {', '.join(report.memory_updates)}")
        if report.kb_indexed_count:
            logs.append(f"KB indexed: {report.kb_indexed_count} entries")

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(report_dict, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="learning_report.json",
                content_type="application/json",
            ),
        )

        self._publish_learning_event(task_input, report_dict)

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "learning_report": report_dict,
                "memory_applied": report.memory_applied,
                "kb_indexed_count": report.kb_indexed_count,
            },
            logs=logs,
        )

    def _publish_learning_event(self, task_input: AgentTaskInput, report: dict) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent:
                return
            event = DomainEvent(
                event_type=LEARNING_RECORDED,
                pipeline_id=task_input.pipeline_id,
                project_id=task_input.project_id,
                job_id=task_input.job_id,
                agent="learning",
                step=self.step,
                status="completed",
                payload=report,
            )
            bus.publish_sync(event)
        except Exception:
            pass
