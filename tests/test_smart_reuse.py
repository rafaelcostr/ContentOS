"""Tests for Smart Reuse Engine (V4.0.4 / Epic 4)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_intelligence.application.reuse_advisor import (
    ReuseAdvisor,
    _build_query,
    _cache_key,
)
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.knowledge import KnowledgeHit, KnowledgeQueryRequest
from contentos_intelligence.domain.reuse_suggestion import ReuseSuggestion


class MockKnowledgeQuery:
    def __init__(self, hits_by_type: dict[str, list[KnowledgeHit]] | None = None) -> None:
        self._hits = hits_by_type or {}
        self.calls: list[KnowledgeQueryRequest] = []

    async def search(self, request: KnowledgeQueryRequest) -> list[KnowledgeHit]:
        self.calls.append(request)
        if request.resource_types:
            rt = request.resource_types[0]
            return self._hits.get(rt, [])
        return []


def _ctx(**kwargs) -> IntelligenceContext:
    return IntelligenceContext(
        project_id=kwargs.get("project_id", uuid4()),
        pipeline_id=kwargs.get("pipeline_id"),
        topic=kwargs.get("topic", "GTA viral"),
        payload=kwargs.get("payload", {}),
    )


def test_build_query_from_topic_and_payload():
    ctx = _ctx(
        topic="Tema principal",
        payload={
            "hook": {"selected_hook": "Você sabia disso?"},
            "script": {"full_text": "Desenvolvimento do roteiro"},
        },
    )
    q = _build_query(ctx)
    assert "Tema principal" in q
    assert "Você sabia" in q
    assert "roteiro" in q


def test_build_query_empty():
    assert _build_query(_ctx(topic="", payload={})) == ""


def test_cache_key_stable():
    pid = uuid4()
    ctx = _ctx(project_id=pid, topic="x", payload={"a": 1})
    assert _cache_key(ctx, "x") == _cache_key(ctx, "x")


@pytest.mark.asyncio
async def test_suggest_empty_without_query():
    advisor = ReuseAdvisor(MockKnowledgeQuery())
    result = await advisor.suggest(_ctx(topic="", payload={}))
    assert result == []


@pytest.mark.asyncio
async def test_suggest_maps_hits_to_suggestions():
    pid = uuid4()
    rid = uuid4()
    mock = MockKnowledgeQuery(
        {
            "hook": [
                KnowledgeHit(
                    resource_type="hook",
                    resource_id=rid,
                    title="Hook GTA",
                    snippet="Viral hook",
                    similarity=0.85,
                )
            ],
            "script": [],
            "cta": [],
            "asset": [],
        }
    )
    advisor = ReuseAdvisor(mock, min_similarity=0.3, cache_ttl_seconds=60)
    results = await advisor.suggest(_ctx(project_id=pid, topic="GTA secrets"))
    assert len(results) == 1
    assert results[0].resource_type == "hook"
    assert results[0].similarity == 0.85
    assert "Alta similaridade" in results[0].reason


@pytest.mark.asyncio
async def test_suggest_respects_max_total():
    pid = uuid4()
    hits = [
        KnowledgeHit(
            resource_type="hook",
            resource_id=uuid4(),
            title=f"H{i}",
            snippet="s",
            similarity=0.9 - i * 0.01,
        )
        for i in range(5)
    ]
    mock = MockKnowledgeQuery({"hook": hits, "script": [], "cta": [], "asset": []})
    advisor = ReuseAdvisor(mock, max_per_type=5, max_total=2, min_similarity=0.0)
    results = await advisor.suggest(_ctx(project_id=pid, topic="test"))
    assert len(results) == 2


@pytest.mark.asyncio
async def test_suggest_uses_cache():
    pid = uuid4()
    mock = MockKnowledgeQuery(
        {
            "hook": [
                KnowledgeHit(
                    resource_type="hook",
                    resource_id=uuid4(),
                    title="Cached",
                    snippet="x",
                    similarity=0.7,
                )
            ],
            "script": [],
            "cta": [],
            "asset": [],
        }
    )
    advisor = ReuseAdvisor(mock, cache_ttl_seconds=60.0)
    ctx = _ctx(project_id=pid, topic="cache test")
    first = await advisor.suggest(ctx)
    second = await advisor.suggest(ctx)
    assert len(first) == 1
    assert len(second) == 1
    assert len(mock.calls) == 4


@pytest.mark.asyncio
async def test_invalidate_cache():
    mock = MockKnowledgeQuery({"hook": [], "script": [], "cta": [], "asset": []})
    advisor = ReuseAdvisor(mock, cache_ttl_seconds=60.0)
    pid = uuid4()
    ctx = _ctx(project_id=pid, topic="inv")
    await advisor.suggest(ctx)
    advisor.invalidate_cache(pid)
    await advisor.suggest(ctx)
    assert len(mock.calls) == 8


@pytest.mark.asyncio
async def test_db_reuse_advisor_adapter():
    from contentos_intelligence.application.reuse_query_adapter import DbReuseAdvisor

    mock = MockKnowledgeQuery(
        {
            "hook": [],
            "script": [
                KnowledgeHit(
                    resource_type="script",
                    resource_id=uuid4(),
                    title="Script",
                    snippet="body",
                    similarity=0.5,
                )
            ],
            "cta": [],
            "asset": [],
        }
    )
    adapter = DbReuseAdvisor(mock)
    results = await adapter.suggest(_ctx(topic="script topic"))
    assert len(results) == 1
    assert isinstance(results[0], ReuseSuggestion)
