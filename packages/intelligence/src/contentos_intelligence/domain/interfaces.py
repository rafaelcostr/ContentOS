"""V4 intelligence service contracts — dependency injection boundaries."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from contentos_intelligence.domain.content_score import ContentScoreReport
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.knowledge import KnowledgeHit, KnowledgeQueryRequest
from contentos_intelligence.domain.reuse_suggestion import ReuseSuggestion
from contentos_intelligence.domain.specialist import SpecialistSelection
from contentos_intelligence.domain.viral_report import ViralReport


@runtime_checkable
class IViralityScorer(Protocol):
    """Epic 1 — compute viral score and recommendations from pipeline context."""

    async def analyze(self, context: IntelligenceContext) -> ViralReport: ...


@runtime_checkable
class IKnowledgeQuery(Protocol):
    """Epic 3 — semantic search over indexed content."""

    async def search(self, request: KnowledgeQueryRequest) -> list[KnowledgeHit]: ...


@runtime_checkable
class IReuseAdvisor(Protocol):
    """Epic 4 — suggest reusable scripts, hooks, assets, CTAs."""

    async def suggest(self, context: IntelligenceContext) -> list[ReuseSuggestion]: ...


@runtime_checkable
class IContentScorer(Protocol):
    """Epic 9 — unified 0–100 content score facade."""

    async def score(self, context: IntelligenceContext) -> ContentScoreReport: ...


@runtime_checkable
class ISpecialistSelector(Protocol):
    """Epic 5 — pick niche specialist for the workflow."""

    async def select(self, context: IntelligenceContext) -> SpecialistSelection: ...


@runtime_checkable
class IViralEngine(Protocol):
    """Orchestrates viral sub-analyzers into a single ViralReport."""

    async def build_report(self, context: IntelligenceContext) -> ViralReport: ...


@runtime_checkable
class IContentIntelligenceService(Protocol):
    """Composite step: reuse + viral + A/B testing."""

    async def run(self, context: IntelligenceContext) -> dict: ...


@runtime_checkable
class IEmbeddingClient(Protocol):
    """Embedding vectors via AI Gateway (Epic 3 infrastructure)."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
