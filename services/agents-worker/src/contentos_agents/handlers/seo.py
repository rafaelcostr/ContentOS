"""SEO Engine agent — titles, hashtags, descriptions (V5.2.3)."""

from __future__ import annotations

import json
import os

from contentos_intelligence.application.seo import SeoOptimizer, seo_engine_enabled
from contentos_intelligence.domain.seo_package import SeoPackage
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.payload_utils import coerce_dict
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta


def _use_llm() -> bool:
    return os.getenv("SEO_USE_LLM", "true").lower() in ("1", "true", "yes")


def _merge_llm(base: SeoPackage, data: dict) -> SeoPackage:
    title = str(data.get("title") or base.title).strip() or base.title
    description = str(data.get("description") or base.description).strip() or base.description
    hashtags = data.get("hashtags") if isinstance(data.get("hashtags"), list) else base.hashtags
    keywords = data.get("keywords") if isinstance(data.get("keywords"), list) else base.keywords
    variants = data.get("title_variants") if isinstance(data.get("title_variants"), list) else base.title_variants
    merged = SeoPackage(
        title=title[:80],
        description=description[:500],
        hashtags=[str(h).lstrip("#") for h in hashtags][:12],
        keywords=[str(k) for k in keywords][:10],
        title_variants=[str(v)[:80] for v in variants][:3] or base.title_variants,
        platforms=base.platforms,
        seo_score=base.seo_score,
        recommendations=base.recommendations,
    )
    merged.seo_score = min(100.0, merged.seo_score + 5.0)
    return merged


class SeoAgentHandler(BaseAgentHandler):
    step = "seo"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        if not seo_engine_enabled():
            return AgentTaskOutput(
                job_id=task_input.job_id,
                status=JobStatus.COMPLETED.value,
                data={"seo_skipped": True},
                logs=["[seo] Disabled via SEO_ENGINE_ENABLED"],
            )

        script = coerce_dict(task_input.payload.get("script"))
        topic = str(
            script.get("title")
            or coerce_dict(task_input.payload.get("selected_topic")).get("title")
            or task_input.payload.get("topic", "")
        )
        logs = [f"[seo] Optimizing publication metadata for: {topic}"]

        package = SeoOptimizer().optimize(dict(task_input.payload))
        if _use_llm():
            try:
                prompt = self.render_prompt(
                    "seo",
                    {
                        "topic": topic,
                        "script_json": json.dumps(script, ensure_ascii=False)[:4000],
                        "seo_json": json.dumps(package.to_dict(), ensure_ascii=False)[:2000],
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
                    logs.append("LLM polish: cache hit")
                package = _merge_llm(package, coerce_dict(data))
                logs.append("LLM polish applied")
            except Exception as exc:
                logs.append(f"LLM polish skipped ({exc})")

        payload = package.to_dict()
        logs.append(
            f"Score={package.seo_score:.0f}/100 title={len(package.title)}ch "
            f"tags={len(package.hashtags)} keywords={len(package.keywords)}"
        )

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(payload, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="seo_package.json",
                content_type="application/json",
            ),
        )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data={
                "seo_package": payload,
                "seo_score": package.seo_score,
                "publication_title": package.title,
                "publication_description": package.description,
                "publication_hashtags": package.hashtags,
            },
            logs=logs,
        )
