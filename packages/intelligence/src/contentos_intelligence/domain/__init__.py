"""Domain models and contracts for ContentOS V4 intelligence."""

from contentos_intelligence.domain.content_score import ContentScoreDimension, ContentScoreReport
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.interfaces import (
    IContentIntelligenceService,
    IContentScorer,
    IEmbeddingClient,
    IKnowledgeQuery,
    IReuseAdvisor,
    ISpecialistSelector,
    IViralEngine,
    IViralityScorer,
)
from contentos_intelligence.domain.knowledge import KnowledgeHit, KnowledgeQueryRequest
from contentos_intelligence.domain.reuse_suggestion import ReuseSuggestion
from contentos_intelligence.domain.specialist import SpecialistProfile, SpecialistSelection
from contentos_intelligence.domain.viral_report import ViralReport

__all__ = [
    "ContentScoreDimension",
    "ContentScoreReport",
    "IntelligenceContext",
    "IContentIntelligenceService",
    "IContentScorer",
    "IEmbeddingClient",
    "IKnowledgeQuery",
    "IReuseAdvisor",
    "ISpecialistSelector",
    "IViralEngine",
    "IViralityScorer",
    "KnowledgeHit",
    "KnowledgeQueryRequest",
    "ReuseSuggestion",
    "SpecialistProfile",
    "SpecialistSelection",
    "ViralReport",
]
