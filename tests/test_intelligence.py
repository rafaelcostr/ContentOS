"""Tests for contentos_intelligence package (V4.0.1)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_intelligence import (
    IntelligenceContext,
    IntelligenceRegistry,
    get_intelligence_registry,
    reset_intelligence_registry,
)
from contentos_intelligence.application.content_intelligence_service import ContentIntelligenceService
from contentos_intelligence.application.noop import NoOpViralityScorer
from contentos_intelligence.domain.interfaces import (
    IContentIntelligenceService,
    IContentScorer,
    IEmbeddingClient,
    IKnowledgeQuery,
    IReuseAdvisor,
    ISpecialistSelector,
    IViralityScorer,
)
from contentos_intelligence.domain.knowledge import KnowledgeQueryRequest
from contentos_intelligence.domain.viral_report import ViralReport


@pytest.fixture(autouse=True)
def _reset_registry():
    reset_intelligence_registry()
    yield
    reset_intelligence_registry()


def _context() -> IntelligenceContext:
    return IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="GTA 6 secrets",
        payload={"hook": {"selected_hook": "Você não vai acreditar"}},
    )


def test_interfaces_are_runtime_checkable():
    assert isinstance(NoOpViralityScorer(), IViralityScorer)


@pytest.mark.asyncio
async def test_noop_virality_scorer_returns_report():
    scorer = NoOpViralityScorer()
    report = await scorer.analyze(_context())
    assert isinstance(report, ViralReport)
    assert report.viral_score == 0.0
    assert report.to_dict()["recommendations"] == []


@pytest.mark.asyncio
async def test_content_intelligence_service_run():
    registry = IntelligenceRegistry()
    service = registry.content_intelligence_service()
    result = await service.run(_context())
    assert "viral_report" in result
    assert "reuse_suggestions" in result
    assert result["reuse_suggestions"] == []
    assert result["viral_report"]["viral_score"] == 0.0


def test_registry_singleton():
    a = get_intelligence_registry()
    b = get_intelligence_registry()
    assert a is b


def test_registry_register_custom_scorer():
    class HighScorer:
        async def analyze(self, context: IntelligenceContext) -> ViralReport:
            return ViralReport(viral_score=88.5, retention_prediction=72.0, recommendations=["test"])

    registry = IntelligenceRegistry()
    registry.register_virality_scorer(HighScorer())
    assert registry.virality_scorer is not None


@pytest.mark.asyncio
async def test_custom_scorer_via_registry():
    class HighScorer:
        async def analyze(self, context: IntelligenceContext) -> ViralReport:
            return ViralReport(viral_score=88.5, retention_prediction=72.0)

    registry = IntelligenceRegistry()
    registry.register_virality_scorer(HighScorer())
    service: IContentIntelligenceService = registry.content_intelligence_service()
    result = await service.run(_context())
    assert result["viral_report"]["viral_score"] == 88.5


@pytest.mark.asyncio
async def test_noop_knowledge_query_empty():
    registry = IntelligenceRegistry()
    hits = await registry.knowledge_query.search(
        KnowledgeQueryRequest(project_id=uuid4(), query="hook viral")
    )
    assert hits == []


def test_all_noop_services_satisfy_protocols():
    registry = IntelligenceRegistry()
    assert isinstance(registry.virality_scorer, IViralityScorer)
    assert isinstance(registry.knowledge_query, IKnowledgeQuery)
    assert isinstance(registry.reuse_advisor, IReuseAdvisor)
    assert isinstance(registry.content_scorer, IContentScorer)
    assert isinstance(registry.specialist_selector, ISpecialistSelector)
    assert isinstance(registry.embedding_client, IEmbeddingClient)


def test_viral_report_roundtrip():
    report = ViralReport(
        viral_score=75.5,
        retention_prediction=68.2,
        recommendations=["Shorten intro", "Stronger CTA"],
        hook_score=80.0,
    )
    restored = ViralReport.from_dict(report.to_dict())
    assert restored.viral_score == 75.5
    assert restored.recommendations == report.recommendations


def test_content_intelligence_service_direct_construction():
    from contentos_intelligence.application.noop import NoOpReuseAdvisor, NoOpViralityScorer

    service = ContentIntelligenceService(
        reuse_advisor=NoOpReuseAdvisor(),
        virality_scorer=NoOpViralityScorer(),
    )
    assert service is not None
