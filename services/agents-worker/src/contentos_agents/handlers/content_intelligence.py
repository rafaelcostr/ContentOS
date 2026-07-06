"""Content Intelligence step — reuse + viral + A/B before scene/editor (V4)."""

from __future__ import annotations

import json

from contentos_intelligence.application.ab_testing import apply_ab_winners_to_payload
from contentos_intelligence.application.bootstrap import get_content_intelligence_service
from contentos_intelligence.application.specialists.context import apply_specialist_to_payload
from contentos_intelligence.domain.ab_testing import AbTestReport
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.specialist import SpecialistSelection
from contentos_intelligence.infrastructure.ab_repository import AbVariantRepository
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta

try:
    from contentos_events import DomainEvent, get_event_bus
    from contentos_events.domain.event_types import AB_VARIANT_SELECTED, CONTENT_SCORE_COMPUTED, SPECIALIST_SELECTED
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]
    AB_VARIANT_SELECTED = "ab.variant.selected"  # type: ignore[misc]
    CONTENT_SCORE_COMPUTED = "content_score.computed"  # type: ignore[misc]
    SPECIALIST_SELECTED = "specialist.selected"  # type: ignore[misc]

    def get_event_bus():  # type: ignore[misc]
        return None

_AB_OUTPUT_KEYS = (
    "selected_hook",
    "hook",
    "hook_text",
    "script",
    "thumbnail_concept",
    "opener_text",
    "ab_test",
    "ab_thumbnail_winner",
    "ab_opener_winner",
    "specialist_selection",
    "specialist_id",
    "specialist_context",
    "specialist_prompt_pack",
)


class ContentIntelligenceAgentHandler(BaseAgentHandler):
    step = "content_intelligence"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        script = coerce_dict(task_input.payload.get("script"))
        topic = (
            script.get("title")
            or coerce_dict(task_input.payload.get("selected_topic")).get("title")
            or task_input.payload.get("topic", "")
        )
        logs = [f"[content_intelligence] Analyzing viral potential for: {topic}"]

        context = IntelligenceContext(
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            topic=str(topic),
            payload=dict(task_input.payload),
        )

        service = get_content_intelligence_service()
        result = await service.run(context)
        viral_report = result.get("viral_report") or {}
        reuse_suggestions = result.get("reuse_suggestions") or []
        ab_test = result.get("ab_test") or {}
        content_score_report = result.get("content_score_report") or {}
        specialist_selection = result.get("specialist_selection") or {}

        logs.append(
            f"Viral score={viral_report.get('viral_score', 0)} "
            f"retention={viral_report.get('retention_prediction', 0)}"
        )
        logs.append(f"Reuse suggestions: {len(reuse_suggestions)}")

        specialist_sel: SpecialistSelection | None = None
        if specialist_selection:
            specialist_sel = SpecialistSelection.from_dict(specialist_selection)
            logs.append(
                f"Specialist={specialist_sel.specialist.specialist_id} "
                f"confidence={specialist_sel.confidence:.2f}"
            )
            self._publish_specialist_event(task_input, specialist_selection)

        ab_report: AbTestReport | None = None
        if ab_test:
            ab_report = AbTestReport.from_dict(ab_test)
            AbVariantRepository().save_report_sync(ab_report)
            logs.append(f"A/B testing: {len(ab_report.dimensions)} dimensions, winners auto-selected")
            for dim in ab_report.dimensions:
                if dim.winner:
                    logs.append(f"  {dim.dimension} winner score={dim.winner.score:.1f}")
            self._publish_ab_events(task_input, ab_report)

        if content_score_report:
            logs.append(
                f"Content score={content_score_report.get('total_score', 0)} "
                f"grade={content_score_report.get('grade', '')} "
                f"mode={content_score_report.get('mode', 'preview')}"
            )
            self._publish_content_score_event(task_input, content_score_report)

        for rec in (viral_report.get("recommendations") or [])[:3]:
            logs.append(f"→ {rec}")

        output_data = {
            "viral_report": viral_report,
            "reuse_suggestions": reuse_suggestions,
            "content_intelligence": result,
            "ab_test": ab_test,
            "content_score_report": content_score_report,
            "specialist_selection": specialist_selection,
        }
        merged_payload = dict(task_input.payload)
        if specialist_sel:
            merged_payload = apply_specialist_to_payload(merged_payload, specialist_sel)
        if ab_report:
            merged_payload = apply_ab_winners_to_payload(merged_payload, ab_report)
        for key in _AB_OUTPUT_KEYS:
            if key in merged_payload:
                output_data[key] = merged_payload[key]

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(result, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="content_intelligence.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data=output_data,
            logs=logs,
        )

    def _publish_ab_events(self, task_input: AgentTaskInput, report: AbTestReport) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent:
                return
            for dim in report.dimensions:
                if not dim.winner:
                    continue
                event = DomainEvent(
                    event_type=AB_VARIANT_SELECTED,
                    pipeline_id=task_input.pipeline_id,
                    project_id=task_input.project_id,
                    job_id=task_input.job_id,
                    agent="ab_testing",
                    step=self.step,
                    status="completed",
                    payload={
                        "dimension": dim.dimension,
                        "winner": dim.winner.to_dict(),
                        "variants": [v.to_dict() for v in dim.variants],
                    },
                )
                bus.publish_sync(event)
        except Exception:
            pass

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

    def _publish_specialist_event(self, task_input: AgentTaskInput, selection: dict) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent:
                return
            event = DomainEvent(
                event_type=SPECIALIST_SELECTED,
                pipeline_id=task_input.pipeline_id,
                project_id=task_input.project_id,
                job_id=task_input.job_id,
                agent="specialist_selector",
                step=self.step,
                status="completed",
                payload=selection,
            )
            bus.publish_sync(event)
        except Exception:
            pass
