"""ViralEngine — delegates to IViralityScorer (Epic 1 implementation slot)."""

from __future__ import annotations

from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.interfaces import IViralityScorer
from contentos_intelligence.domain.viral_report import ViralReport


class ViralEngine:
    """Thin orchestrator; real analyzers plug in via IViralityScorer."""

    def __init__(self, scorer: IViralityScorer) -> None:
        self._scorer = scorer

    async def build_report(self, context: IntelligenceContext) -> ViralReport:
        return await self._scorer.analyze(context)
