"""ContentOS V4 Intelligence — contracts, DI registry and orchestration stubs."""

from contentos_intelligence.application.registry import (
    IntelligenceRegistry,
    get_intelligence_registry,
    reset_intelligence_registry,
)
from contentos_intelligence.domain import (
    ContentScoreReport,
    IContentIntelligenceService,
    IContentScorer,
    IEmbeddingClient,
    IKnowledgeQuery,
    IntelligenceContext,
    IReuseAdvisor,
    ISpecialistSelector,
    IViralEngine,
    IViralityScorer,
    KnowledgeQueryRequest,
    ReuseSuggestion,
    SpecialistSelection,
    ViralReport,
)

__all__ = [
    "ContentScoreReport",
    "IntelligenceContext",
    "IntelligenceRegistry",
    "IContentIntelligenceService",
    "IContentScorer",
    "IEmbeddingClient",
    "IKnowledgeQuery",
    "IReuseAdvisor",
    "ISpecialistSelector",
    "IViralEngine",
    "IViralityScorer",
    "KnowledgeQueryRequest",
    "ReuseSuggestion",
    "SpecialistSelection",
    "ViralReport",
    "get_intelligence_registry",
    "reset_intelligence_registry",
]
