"""LearningEngine — post-pipeline learning into Memory + KB (Epic 7)."""

from __future__ import annotations

import os
from uuid import UUID

from contentos_intelligence.application.content_graph import auto_build_on_learning, is_content_graph_enabled
from contentos_intelligence.application.learning.extractor import (
    extract_cta,
    extract_hook,
    extract_scores,
    extract_signals,
    extract_specialist,
)
from contentos_intelligence.application.learning.memory_applier import apply_to_memory
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.learning import LearningReport
from contentos_intelligence.infrastructure.learning_repository import (
    LearningRepository,
    index_learning_signals_sync,
)


def is_learning_enabled() -> bool:
    return os.getenv("LEARNING_ENGINE_ENABLED", "true").lower() in ("1", "true", "yes")


def auto_apply_memory() -> bool:
    return os.getenv("LEARNING_AUTO_APPLY_MEMORY", "true").lower() in ("1", "true", "yes")


def auto_index_kb() -> bool:
    return os.getenv("LEARNING_AUTO_INDEX_KB", "true").lower() in ("1", "true", "yes")


class LearningEngine:
    def __init__(self, repository: LearningRepository | None = None) -> None:
        self._repo = repository or LearningRepository()

    def process(self, context: IntelligenceContext) -> LearningReport:
        payload = dict(context.payload or {})
        hook = extract_hook(payload)
        cta = extract_cta(payload)
        specialist_id, _, _ = extract_specialist(payload)
        content_score, viral_score = extract_scores(payload)
        signals = extract_signals(payload)

        report = LearningReport(
            project_id=str(context.project_id),
            pipeline_id=str(context.pipeline_id) if context.pipeline_id else None,
            topic=str(context.topic or payload.get("topic") or ""),
            content_score=content_score,
            viral_score=viral_score,
            specialist_id=specialist_id or None,
            hook_text=hook,
            cta_text=cta,
            signals=signals,
        )

        if auto_apply_memory():
            try:
                from contentos_memory.infrastructure.db_repository import load_sync, upsert_sync

                memory = load_sync(context.project_id)
                apply_to_memory(memory, report)
                if report.memory_applied:
                    upsert_sync(memory)
            except Exception:
                report.memory_applied = False
                report.memory_updates = []

        if auto_index_kb() and context.pipeline_id:
            report.kb_indexed_count = index_learning_signals_sync(
                UUID(str(context.project_id)),
                UUID(str(context.pipeline_id)),
                report,
            )

        if context.pipeline_id:
            self._repo.save_report_sync(report)

        if context.pipeline_id and is_content_graph_enabled() and auto_build_on_learning():
            try:
                from contentos_intelligence.application.content_graph import ContentGraphService

                ContentGraphService().build_pipeline_sync(UUID(str(context.pipeline_id)))
            except Exception:
                pass

        return report
