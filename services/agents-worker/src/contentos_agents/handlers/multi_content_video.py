"""Multi Content Video agent — platform variants from render (V4.2.2 / Epic 2b)."""

from __future__ import annotations

import json
import os

from contentos_intelligence.application.multi_content_video.heuristics import GENERATORS, merge_llm_variant
from contentos_intelligence.application.multi_content_video.service import (
    MultiContentVideoService,
    is_multi_content_video_enabled,
)
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.video_variants import VIDEO_PLATFORMS, VideoPlatformVariant
from contentos_intelligence.infrastructure.video_variants_repository import (
    VideoVariantsRepository,
    update_video_platform_variants_sync,
)
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta

try:
    from contentos_events import DomainEvent, get_event_bus
    from contentos_events.domain.event_types import VIDEO_VARIANTS_GENERATED
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]
    VIDEO_VARIANTS_GENERATED = "video_variants.generated"  # type: ignore[misc]

    def get_event_bus():  # type: ignore[misc]
        return None

PROMPT_BY_PLATFORM = {
    "tiktok": "tiktok_metadata",
    "youtube_shorts": "youtube_shorts_metadata",
    "instagram_reels": "instagram_reels_metadata",
}


def _use_llm() -> bool:
    return os.getenv("MULTI_CONTENT_VIDEO_USE_LLM", "true").lower() in ("1", "true", "yes")


def _platforms() -> list[str]:
    raw = os.getenv("MULTI_CONTENT_VIDEO_PLATFORMS", "tiktok,youtube_shorts,instagram_reels")
    return [p.strip() for p in raw.split(",") if p.strip() in VIDEO_PLATFORMS]


class MultiContentVideoAgentHandler(BaseAgentHandler):
    step = "multi_content_video"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        if not is_multi_content_video_enabled():
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                data={"multi_content_video_skipped": True},
                logs=["[multi_content_video] Disabled via MULTI_CONTENT_VIDEO_ENABLED"],
            )

        script = coerce_dict(task_input.payload.get("script"))
        topic = str(task_input.payload.get("topic") or script.get("title") or "")
        publication = coerce_dict(task_input.payload.get("publication"))
        logs = [f"[multi_content_video] Building platform variants for: {topic}"]

        if not task_input.payload.get("render_ref"):
            logs.append("Warning: render_ref missing — variants will have ready_to_publish=false")

        platforms = _platforms()
        llm_variants: dict[str, VideoPlatformVariant] = {}
        script_json = json.dumps(script, ensure_ascii=False)[:4000]
        publication_json = json.dumps(publication, ensure_ascii=False)[:2000]

        if _use_llm():
            for platform in platforms:
                prompt_id = PROMPT_BY_PLATFORM.get(platform)
                if not prompt_id:
                    continue
                try:
                    prompt = self.render_prompt(
                        prompt_id,
                        {
                            "topic": topic,
                            "script_json": script_json,
                            "publication_json": publication_json,
                        },
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
                        logs.append(f"  {platform}: cache hit")
                    base = GENERATORS[platform](task_input.payload)
                    llm_variants[platform] = merge_llm_variant(platform, data, base)
                    logs.append(f"  {platform}: LLM ok")
                except Exception as exc:
                    logs.append(f"  {platform}: LLM fallback ({exc})")

        context = IntelligenceContext(
            project_id=task_input.project_id,
            pipeline_id=task_input.pipeline_id,
            topic=topic,
            payload=dict(task_input.payload),
        )
        report = MultiContentVideoService().generate(context, platforms=platforms, llm_variants=llm_variants)
        VideoVariantsRepository().save_report_sync(report)
        update_video_platform_variants_sync(task_input.pipeline_id, report.to_dict().get("by_platform") or {})

        logs.append(f"Generated {len(report.variants)} video platform variants")
        report_dict = report.to_dict()

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(report_dict, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="video_variants.json",
                content_type="application/json",
            ),
        )

        self._publish_event(task_input, report_dict)

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "video_variants": report_dict,
                "video_variants_report": report_dict,
                "platform_publications": report_dict.get("by_platform") or {},
            },
            logs=logs,
        )

    def _publish_event(self, task_input: AgentTaskInput, report: dict) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent:
                return
            event = DomainEvent(
                event_type=VIDEO_VARIANTS_GENERATED,
                pipeline_id=task_input.pipeline_id,
                project_id=task_input.project_id,
                job_id=task_input.job_id,
                agent="multi_content_video",
                step=self.step,
                status="completed",
                payload=report,
            )
            bus.publish_sync(event)
        except Exception:
            pass
