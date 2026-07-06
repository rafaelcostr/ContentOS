"""Tests for Knowledge Base (V4.0.3 / Epic 3)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_intelligence.application.noop import NoOpEmbeddingClient
from contentos_intelligence.application.similarity import cosine_similarity, text_overlap_score
from contentos_intelligence.domain.knowledge import KnowledgeQueryRequest
from contentos_intelligence.domain.knowledge_entry import VALID_RESOURCE_TYPES, KnowledgeEntryData


def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_empty():
    assert cosine_similarity([], [1.0]) == 0.0


def test_text_overlap_score():
    score = text_overlap_score("viral gta secrets", "Este vídeo viral sobre GTA revela secrets")
    assert score > 0.5


def test_knowledge_entry_to_dict():
    pid = uuid4()
    entry = KnowledgeEntryData(
        id=uuid4(),
        project_id=pid,
        org_id=None,
        pipeline_id=None,
        resource_type="hook",
        resource_id=uuid4(),
        title="Hook test",
        content_text="Você não vai acreditar",
        embedding=[0.1, 0.2],
    )
    d = entry.to_dict()
    assert d["resource_type"] == "hook"
    assert d["has_embedding"] is True


def test_valid_resource_types():
    assert "script" in VALID_RESOURCE_TYPES
    assert "hook" in VALID_RESOURCE_TYPES
    assert "analytics" in VALID_RESOURCE_TYPES


@pytest.mark.asyncio
async def test_noop_embedding_client():
    client = NoOpEmbeddingClient()
    vectors = await client.embed(["hello", "world"])
    assert vectors == [[], []]


@pytest.mark.asyncio
async def test_semantic_search_text_fallback():
    from unittest.mock import AsyncMock, MagicMock

    from contentos_intelligence.application.semantic_search import SemanticSearch

    entry = KnowledgeEntryData(
        id=uuid4(),
        project_id=uuid4(),
        org_id=None,
        pipeline_id=None,
        resource_type="script",
        resource_id=uuid4(),
        title="GTA viral",
        content_text="roteiro viral sobre GTA 6 lançamento",
        snippet="roteiro viral",
    )
    repo = MagicMock()
    repo.fetch_candidates = AsyncMock(return_value=[entry])
    db = MagicMock()
    search = SemanticSearch(db, NoOpEmbeddingClient(), repo)
    hits = await search.search(
        KnowledgeQueryRequest(project_id=entry.project_id, query="GTA viral", min_similarity=0.0)
    )
    assert len(hits) == 1
    assert hits[0].resource_type == "script"
    assert hits[0].similarity > 0
