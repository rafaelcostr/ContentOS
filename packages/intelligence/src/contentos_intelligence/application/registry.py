"""DI registry for V4 intelligence services."""

from __future__ import annotations

from contentos_intelligence.application.content_intelligence_service import ContentIntelligenceService
from contentos_intelligence.application.noop import (
    NoOpContentScorer,
    NoOpEmbeddingClient,
    NoOpKnowledgeQuery,
    NoOpReuseAdvisor,
    NoOpSpecialistSelector,
    NoOpViralityScorer,
)
from contentos_intelligence.domain.interfaces import (
    IContentIntelligenceService,
    IContentScorer,
    IEmbeddingClient,
    IKnowledgeQuery,
    IReuseAdvisor,
    ISpecialistSelector,
    IViralityScorer,
)

_default_registry: IntelligenceRegistry | None = None


class IntelligenceRegistry:
    """Central registry — modules register implementations without cross-imports."""

    def __init__(self) -> None:
        self._virality_scorer: IViralityScorer = NoOpViralityScorer()
        self._knowledge_query: IKnowledgeQuery = NoOpKnowledgeQuery()
        self._reuse_advisor: IReuseAdvisor = NoOpReuseAdvisor()
        self._content_scorer: IContentScorer = NoOpContentScorer()
        self._specialist_selector: ISpecialistSelector = NoOpSpecialistSelector()
        self._embedding_client: IEmbeddingClient = NoOpEmbeddingClient()

    def register_virality_scorer(self, impl: IViralityScorer) -> None:
        self._virality_scorer = impl

    def register_knowledge_query(self, impl: IKnowledgeQuery) -> None:
        self._knowledge_query = impl

    def register_reuse_advisor(self, impl: IReuseAdvisor) -> None:
        self._reuse_advisor = impl

    def register_content_scorer(self, impl: IContentScorer) -> None:
        self._content_scorer = impl

    def register_specialist_selector(self, impl: ISpecialistSelector) -> None:
        self._specialist_selector = impl

    def register_embedding_client(self, impl: IEmbeddingClient) -> None:
        self._embedding_client = impl

    @property
    def virality_scorer(self) -> IViralityScorer:
        return self._virality_scorer

    @property
    def knowledge_query(self) -> IKnowledgeQuery:
        return self._knowledge_query

    @property
    def reuse_advisor(self) -> IReuseAdvisor:
        return self._reuse_advisor

    @property
    def content_scorer(self) -> IContentScorer:
        return self._content_scorer

    @property
    def specialist_selector(self) -> ISpecialistSelector:
        return self._specialist_selector

    @property
    def embedding_client(self) -> IEmbeddingClient:
        return self._embedding_client

    def content_intelligence_service(self) -> IContentIntelligenceService:
        return ContentIntelligenceService(
            reuse_advisor=self._reuse_advisor,
            virality_scorer=self._virality_scorer,
            content_scorer=self._content_scorer,
            specialist_selector=self._specialist_selector,
        )


def get_intelligence_registry() -> IntelligenceRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = IntelligenceRegistry()
    return _default_registry


def reset_intelligence_registry() -> None:
    """Reset singleton — for tests only."""
    global _default_registry
    _default_registry = None
