"""Multi Content agent — text formats from script (V4.2.1 / Epic 2a)."""

from __future__ import annotations

import json
import os

from contentos_intelligence.application.multi_content.heuristics import GENERATORS, merge_llm_artifact
from contentos_intelligence.application.multi_content.service import MultiContentService, is_multi_content_enabled
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.multi_content import TEXT_FORMATS, TextArtifact
from contentos_intelligence.infrastructure.multi_content_repository import MultiContentRepository
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta

try:
    from contentos_events import DomainEvent, get_event_bus
    from contentos_events.domain.event_types import MULTI_CONTENT_GENERATED
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]
    MULTI_CONTENT_GENERATED = "multi_content.generated"  # type: ignore[misc]

    def get_event_bus():  # type: ignore[misc]
        return None


def _use_llm() -> bool:
    return os.getenv("MULTI_CONTENT_USE_LLM", "true").lower() in ("1", "true", "yes")


def _formats() -> list[str]:
    raw = os.getenv(
        "MULTI_CONTENT_FORMATS",
        "thread_x,linkedin_post,newsletter,seo_article,email_marketing",
    )
    return [f.strip() for f in raw.split(",") if f.strip() in TEXT_FORMATS]


class MultiContentAgentHandler(BaseAgentHandler):
    step = "multi_content"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        if not is_multi_content_enabled():
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                data={"multi_content_skipped": True},
                logs=["[multi_content] Disabled via MULTI_CONTENT_ENABLED"],
            )

        script = coerce_dict(task_input.payload.get("script"))
        topic = str(task_input.payload.get("topic") or script.get("title") or "")
        logs = [f"[multi_content] Generating text formats for: {topic}"]
        formats = _formats()
        llm_artifacts: dict[str, TextArtifact] = {}

        script_json = json.dumps(script, ensure_ascii=False)[:4000]
        if _use_llm():
            for fmt in formats:
                try:
                    prompt = self.render_prompt(
                        fmt,
                        {"topic": topic, "script_json": script_json},
                        project_id=task_input.project_id,
                    )
                    data, from_cache, _ = await self.chat_json_with_cache(
                        prompt,
                        topic=topic,
                        project_id=task_input.project_id,
                        pipeline_id=task_input.pipeline_id,
                        job_id=task_input.job_id,
                    )
                    if from_cache:
                        logs.append(f"  {fmt}: cache hit")
                    base = GENERATORS[fmt](task_input.payload)
                    llm_artifacts[fmt] = merge_llm_artifact(fmt, data, base)
                    logs.append(f"  {fmt}: LLM ok")
                except Exception as exc:
                    logs.append(f"  {fmt}: LLM fallback ({exc})")

        context = IntelligenceContext(
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            topic=topic,
            payload=dict(task_input.payload),
        )
        report = MultiContentService().generate(context, formats=formats, llm_artifacts=llm_artifacts)
        MultiContentRepository().save_report_sync(report)

        logs.append(f"Generated {len(report.artifacts)} text artifacts")
        report_dict = report.to_dict()

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(report_dict, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="multi_content.json",
                content_type="application/json",
            ),
        )

        self._publish_event(task_input, report_dict)

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "multi_content": report_dict,
                "multi_content_report": report_dict,
            },
            logs=logs,
        )

    def _publish_event(self, task_input: AgentTaskInput, report: dict) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent:
                return
            event = DomainEvent(
                event_type=MULTI_CONTENT_GENERATED,
                pipeline_id=task_input.pipeline_id,
                project_id=task_input.project_id,
                job_id=task_input.job_id,
                agent="multi_content",
                step=self.step,
                status="completed",
                payload=report,
            )
            bus.publish_sync(event)
        except Exception:
            pass
