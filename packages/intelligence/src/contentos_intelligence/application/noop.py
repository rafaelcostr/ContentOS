"""No-op implementations — used until Epic implementations replace them."""

from __future__ import annotations

from contentos_intelligence.domain.content_score import ContentScoreReport
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.knowledge import KnowledgeHit, KnowledgeQueryRequest
from contentos_intelligence.domain.reuse_suggestion import ReuseSuggestion
from contentos_intelligence.domain.specialist import SpecialistProfile, SpecialistSelection
from contentos_intelligence.domain.viral_report import ViralReport


class NoOpViralityScorer:
    async def analyze(self, context: IntelligenceContext) -> ViralReport:
        return ViralReport(
            viral_score=0.0,
            retention_prediction=0.0,
            recommendations=[],
            details={"status": "noop", "pipeline_id": str(context.pipeline_id)},
        )


class NoOpKnowledgeQuery:
    async def search(self, request: KnowledgeQueryRequest) -> list[KnowledgeHit]:
        return []


class NoOpReuseAdvisor:
    async def suggest(self, context: IntelligenceContext) -> list[ReuseSuggestion]:
        return []


class NoOpContentScorer:
    async def score(self, context: IntelligenceContext) -> ContentScoreReport:
        return ContentScoreReport(total_score=0.0, summary="not_implemented")


class NoOpSpecialistSelector:
    async def select(self, context: IntelligenceContext) -> SpecialistSelection:
        return SpecialistSelection(
            specialist=SpecialistProfile(
                specialist_id="default",
                name="Default",
                niche="general",
            ),
            confidence=0.0,
            reason="noop_selector",
        )


class NoOpEmbeddingClient:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[] for _ in texts]
