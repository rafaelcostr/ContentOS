"""A/B testing service — generate, score, select, persist."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.application.ab_testing.generators import GENERATORS
from contentos_intelligence.application.ab_testing.scoring import score_variant
from contentos_intelligence.domain.ab_testing import (
    AB_DIMENSIONS,
    AbDimensionResult,
    AbTestReport,
)
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.infrastructure.ab_repository import AbVariantRepository


def _variants_per_dimension() -> int:
    try:
        return max(2, min(5, int(os.getenv("AB_VARIANTS_PER_DIMENSION", "3"))))
    except ValueError:
        return 3


class AbTestingService:
    """Epic 6 — automatic A/B before editor."""

    def __init__(self, db: AsyncSession | None = None, repository: AbVariantRepository | None = None) -> None:
        self._db = db
        self._repo = repository or AbVariantRepository()

    def run(self, context: IntelligenceContext, viral_report: dict) -> AbTestReport:
        dimensions: list[AbDimensionResult] = []
        winners: dict[str, Any] = {}
        limit = _variants_per_dimension()

        for dimension in sorted(AB_DIMENSIONS):
            generator = GENERATORS.get(dimension)
            if not generator:
                continue
            variants = generator(context.payload or {})[:limit]
            if not variants:
                continue
            for v in variants:
                v.score = score_variant(dimension, v, viral_report)
            variants.sort(key=lambda x: x.score, reverse=True)
            winner_index = 0
            winner = variants[0]
            dimensions.append(
                AbDimensionResult(
                    dimension=dimension,
                    variants=variants,
                    winner_index=winner_index,
                    winner=winner,
                )
            )
            winners[dimension] = winner.to_dict()

        return AbTestReport(
            project_id=context.project_id,
            pipeline_id=context.pipeline_id,
            dimensions=dimensions,
            winners=winners,
        )

    async def run_and_persist(self, context: IntelligenceContext, viral_report: dict) -> AbTestReport:
        report = self.run(context, viral_report)
        if self._db and context.pipeline_id:
            await self._repo.save_report(self._db, report)
        return report


def apply_ab_winners_to_payload(payload: dict, report: AbTestReport) -> dict:
    """Merge winning variants into pipeline payload for downstream agents."""
    updated = dict(payload)
    winners = report.winners

    if hook_w := winners.get("hook"):
        value = hook_w.get("value", "")
        hook_data = dict(updated.get("selected_hook") or updated.get("hook") or {})
        if not isinstance(hook_data, dict):
            hook_data = {}
        hook_data["hook_text"] = value
        hook_data["selected_by_ab"] = True
        updated["selected_hook"] = hook_data
        updated["hook"] = hook_data
        updated["hook_text"] = value

    if title_w := winners.get("title"):
        script = dict(updated.get("script") or {})
        if isinstance(script, dict):
            script["title"] = title_w.get("value", script.get("title", ""))
            script["title_selected_by_ab"] = True
            updated["script"] = script

    if cta_w := winners.get("cta"):
        script = dict(updated.get("script") or {})
        if isinstance(script, dict):
            script["call_to_action"] = cta_w.get("value", script.get("call_to_action", ""))
            script["cta_selected_by_ab"] = True
            updated["script"] = script

    if thumb_w := winners.get("thumbnail"):
        updated["thumbnail_concept"] = thumb_w.get("value", "")
        updated["ab_thumbnail_winner"] = thumb_w

    if opener_w := winners.get("opener"):
        updated["opener_text"] = opener_w.get("value", "")
        updated["ab_opener_winner"] = opener_w

    updated["ab_test"] = report.to_dict()
    return updated
