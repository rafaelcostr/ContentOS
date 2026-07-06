"""Bootstrap intelligence registry for gateway and agents-worker."""

from __future__ import annotations

from contentos_intelligence.application.content_score.service import ContentScoreService
from contentos_intelligence.application.knowledge_query_adapter import DbKnowledgeQuery
from contentos_intelligence.application.noop import (
    NoOpContentScorer,
    NoOpReuseAdvisor,
    NoOpSpecialistSelector,
    NoOpViralityScorer,
)
from contentos_intelligence.application.registry import get_intelligence_registry
from contentos_intelligence.application.reuse_query_adapter import DbReuseAdvisor
from contentos_intelligence.application.specialists.selector import NicheSpecialistSelector
from contentos_intelligence.application.viral.payload_scorer import PayloadViralityScorer
from contentos_intelligence.domain.interfaces import IContentScorer, ISpecialistSelector, IViralityScorer
from contentos_intelligence.infrastructure.embedding_client import get_gateway_embedding_client


def configure_intelligence_registry(*, with_database: bool = True) -> None:
    """Register production implementations. Safe to call multiple times."""
    registry = get_intelligence_registry()
    registry.register_virality_scorer(PayloadViralityScorer())
    registry.register_content_scorer(ContentScoreService())
    registry.register_specialist_selector(NicheSpecialistSelector())
    registry.register_embedding_client(get_gateway_embedding_client())

    if not with_database:
        return

    try:
        from contentos_database.session import get_session_factory

        factory = get_session_factory()
        if not factory:
            return
        embed = get_gateway_embedding_client()
        kb = DbKnowledgeQuery(factory, embed)
        registry.register_knowledge_query(kb)
        registry.register_reuse_advisor(DbReuseAdvisor(kb))
        registry.register_content_scorer(ContentScoreService(knowledge_query=kb))
    except Exception:
        pass


def ensure_virality_scorer() -> IViralityScorer:
    registry = get_intelligence_registry()
    if isinstance(registry.virality_scorer, NoOpViralityScorer):
        registry.register_virality_scorer(PayloadViralityScorer())
    return registry.virality_scorer


def ensure_content_scorer() -> IContentScorer:
    registry = get_intelligence_registry()
    if isinstance(registry.content_scorer, NoOpContentScorer):
        registry.register_content_scorer(ContentScoreService())
    return registry.content_scorer


def ensure_specialist_selector() -> ISpecialistSelector:
    registry = get_intelligence_registry()
    if isinstance(registry.specialist_selector, NoOpSpecialistSelector):
        registry.register_specialist_selector(NicheSpecialistSelector())
    return registry.specialist_selector


def get_content_intelligence_service():
    ensure_virality_scorer()
    ensure_content_scorer()
    ensure_specialist_selector()
    registry = get_intelligence_registry()
    if isinstance(registry.reuse_advisor, NoOpReuseAdvisor):
        try:
            configure_intelligence_registry(with_database=True)
        except Exception:
            pass
    return registry.content_intelligence_service()
