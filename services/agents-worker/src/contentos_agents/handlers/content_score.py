"""Content Score step — computes the final 0-100 aggregate report."""

from __future__ import annotations

import json

from contentos_intelligence.application.content_score.service import ContentScoreService
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta

try:
    from contentos_events import DomainEvent, get_event_bus
    from contentos_events.domain.event_types import CONTENT_SCORE_COMPUTED
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]
    CONTENT_SCORE_COMPUTED = "content_score.computed"  # type: ignore[misc]

    def get_event_bus():  # type: ignore[misc]
        return None


class ContentScoreAgentHandler(BaseAgentHandler):
    step = "content_score"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        script = coerce_dict(task_input.payload.get("script"))
        topic = (
            script.get("title")
            or coerce_dict(task_input.payload.get("selected_topic")).get("title")
            or task_input.payload.get("topic", "")
        )
        logs = [f"[content_score] Calculating final content score for: {topic}"]

        context = IntelligenceContext(
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            topic=str(topic),
            payload=dict(task_input.payload),
        )
        report = await ContentScoreService().score(context)
        report_payload = report.to_dict()
        total_score = float(report_payload.get("total_score") or 0)

        logs.append(
            f"Content score={total_score:.1f}/100 "
            f"grade={report_payload.get('grade', '')} "
            f"mode={report_payload.get('mode', 'preview')}"
        )
        for dim in report_payload.get("dimensions", [])[:5]:
            logs.append(
                f"  {dim.get('name')}: {float(dim.get('score') or 0):.1f} "
                f"(w={float(dim.get('weight') or 0):.2f})"
            )

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(report_payload, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="content_score.json",
                content_type="application/json",
            ),
        )
        self._publish_content_score_event(task_input, report_payload)

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "content_score_report": report_payload,
                "content_score": total_score,
                "content_score_passed": total_score >= 60,
            },
            logs=logs,
        )

    def _publish_content_score_event(self, task_input: AgentTaskInput, report: dict) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent:
                return
            event = DomainEvent(
                event_type=CONTENT_SCORE_COMPUTED,
                pipeline_id=task_input.pipeline_id,
                project_id=task_input.project_id,
                job_id=task_input.job_id,
                agent="content_score",
                step=self.step,
                status="completed",
                payload=report,
            )
            bus.publish_sync(event)
        except Exception:
            pass
