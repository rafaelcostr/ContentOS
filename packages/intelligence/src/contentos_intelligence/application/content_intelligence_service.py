"""Composite content_intelligence orchestration (reuse + viral + A/B)."""

from __future__ import annotations

import os

from contentos_intelligence.application.ab_testing import AbTestingService
from contentos_intelligence.application.content_score import is_content_score_enabled
from contentos_intelligence.application.noop import NoOpContentScorer, NoOpSpecialistSelector
from contentos_intelligence.application.viral_engine import ViralEngine
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.interfaces import IContentScorer, IReuseAdvisor, ISpecialistSelector, IViralityScorer


def _ab_testing_enabled() -> bool:
    return os.getenv("AB_TESTING_ENABLED", "true").lower() in ("1", "true", "yes")


def _specialist_selection_enabled() -> bool:
    return os.getenv("SPECIALIST_SELECTION_ENABLED", "true").lower() in ("1", "true", "yes")


class ContentIntelligenceService:
    """Single entry point for the content_intelligence pipeline step."""

    def __init__(
        self,
        reuse_advisor: IReuseAdvisor,
        virality_scorer: IViralityScorer,
        content_scorer: IContentScorer | None = None,
        specialist_selector: ISpecialistSelector | None = None,
        *,
        ab_testing_enabled: bool | None = None,
        content_score_enabled: bool | None = None,
        specialist_selection_enabled: bool | None = None,
    ) -> None:
        self._reuse = reuse_advisor
        self._viral_engine = ViralEngine(virality_scorer)
        self._content_scorer = content_scorer or NoOpContentScorer()
        self._specialist_selector = specialist_selector or NoOpSpecialistSelector()
        self._ab_enabled = _ab_testing_enabled() if ab_testing_enabled is None else ab_testing_enabled
        self._score_enabled = is_content_score_enabled() if content_score_enabled is None else content_score_enabled
        self._specialist_enabled = (
            _specialist_selection_enabled() if specialist_selection_enabled is None else specialist_selection_enabled
        )
        self._ab_service = AbTestingService()

    async def run(self, context: IntelligenceContext) -> dict:
        result: dict = {}
        if self._specialist_enabled:
            selection = await self._specialist_selector.select(context)
            result["specialist_selection"] = selection.to_dict()
        reuse_suggestions = await self._reuse.suggest(context)
        viral_report = await self._viral_engine.build_report(context)
        result.update({
            "reuse_suggestions": [s.to_dict() for s in reuse_suggestions],
            "viral_report": viral_report.to_dict(),
        })
        if self._ab_enabled:
            ab_report = self._ab_service.run(context, viral_report.to_dict())
            result["ab_test"] = ab_report.to_dict()
            result["ab_winners"] = ab_report.winners
        if self._score_enabled:
            scoring_payload = {
                **dict(context.payload or {}),
                "viral_report": result["viral_report"],
            }
            if result.get("ab_test"):
                scoring_payload["ab_test"] = result["ab_test"]
                scoring_payload["ab_winners"] = result.get("ab_winners") or {}
            scoring_context = IntelligenceContext(
                project_id=context.project_id,
                pipeline_id=context.pipeline_id,
                topic=context.topic,
                payload=scoring_payload,
            )
            score_report = await self._content_scorer.score(scoring_context)
            result["content_score_report"] = score_report.to_dict()
        return result
