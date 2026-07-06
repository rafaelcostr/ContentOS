"""MultiContentService — generate text formats from script (Epic 2a)."""

from __future__ import annotations

import os

from contentos_intelligence.application.multi_content.heuristics import GENERATORS
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.multi_content import TEXT_FORMATS, MultiContentReport, TextArtifact


def _enabled_formats() -> list[str]:
    raw = os.getenv(
        "MULTI_CONTENT_FORMATS",
        "thread_x,linkedin_post,newsletter,seo_article,email_marketing",
    )
    formats = [f.strip() for f in raw.split(",") if f.strip()]
    return [f for f in formats if f in TEXT_FORMATS]


def is_multi_content_enabled() -> bool:
    return os.getenv("MULTI_CONTENT_ENABLED", "true").lower() in ("1", "true", "yes")


class MultiContentService:
    """Facade: one script → N text artifacts."""

    def generate(
        self,
        context: IntelligenceContext,
        *,
        formats: list[str] | None = None,
        llm_artifacts: dict[str, TextArtifact] | None = None,
    ) -> MultiContentReport:
        payload = dict(context.payload or {})
        target_formats = formats or _enabled_formats()
        artifacts: list[TextArtifact] = []
        llm_map = llm_artifacts or {}

        for fmt in target_formats:
            generator = GENERATORS.get(fmt)
            if not generator:
                continue
            base = generator(payload)
            if fmt in llm_map:
                artifacts.append(llm_map[fmt])
            else:
                artifacts.append(base)

        return MultiContentReport(
            project_id=str(context.project_id),
            pipeline_id=str(context.pipeline_id) if context.pipeline_id else None,
            topic=str(context.topic or ""),
            artifacts=artifacts,
        )
