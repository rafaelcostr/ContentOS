"""Tests for Content Score (V4.1.2 / Epic 9)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_events.domain.event_types import ALL_TYPES, CONTENT_SCORE_COMPUTED, resolve_event_type
from contentos_intelligence.application.content_intelligence_service import ContentIntelligenceService
from contentos_intelligence.application.content_score.dimensions import (
    DEFAULT_WEIGHTS,
    extract_emotion,
    extract_hook,
    extract_technical,
)
from contentos_intelligence.application.content_score.service import ContentScoreService
from contentos_intelligence.application.noop import NoOpKnowledgeQuery, NoOpReuseAdvisor
from contentos_intelligence.application.viral.payload_scorer import PayloadViralityScorer
from contentos_intelligence.domain.context import IntelligenceContext


def test_default_weights_sum_to_one():
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 0.001


def test_extract_hook_from_viral_report():
    score, source = extract_hook({"viral_report": {"hook_score": 82}})
    assert score == 82
    assert "hook_score" in source


def test_extract_emotion_scales_10_to_100():
    score, source = extract_emotion({"emotion": {"overall": 8}})
    assert score == 80
    assert source == "emotion.overall"


def test_extract_technical_from_quality_score():
    score, source = extract_technical({"quality_score": 9})
    assert score == 90
    assert source == "quality_score"


@pytest.mark.asyncio
async def test_content_score_service_preview_mode():
    service = ContentScoreService()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="GTA 6 viral",
        payload={
            "viral_report": {
                "hook_score": 80,
                "retention_prediction": 75,
                "cta_score": 70,
                "rhythm_score": 85,
                "viral_score": 78,
            },
            "emotion": {"overall": 8, "curiosity": 7, "retention": 8},
            "script": {"title": "GTA 6 revelado", "call_to_action": "Siga para mais!"},
            "ab_test": {
                "winners": {
                    "title": {"score": 72, "value": "GTA 6 — a verdade"},
                    "thumbnail": {"score": 68, "value": "GTA 6 | CHOCANTE"},
                }
            },
            "scenes": [{}, {}, {}, {}, {}],
        },
    )
    report = await service.score(ctx)
    assert 60 <= report.total_score <= 100
    assert report.grade in ("excelente", "bom", "medio", "precisa_melhorar")
    assert report.mode == "preview"
    assert len(report.dimensions) == 10
    names = {d.name for d in report.dimensions}
    assert "hook" in names
    assert "originality" in names


@pytest.mark.asyncio
async def test_content_score_full_mode_with_quality():
    service = ContentScoreService()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="Test",
        payload={
            "viral_report": {"hook_score": 70, "retention_prediction": 70, "viral_score": 70},
            "quality_score": 10,
            "video_score": 9,
        },
    )
    report = await service.score(ctx)
    assert report.mode == "full"
    tech = next(d for d in report.dimensions if d.name == "technical")
    assert tech.score == 100


@pytest.mark.asyncio
async def test_content_intelligence_includes_content_score_report():
    service = ContentIntelligenceService(
        reuse_advisor=NoOpReuseAdvisor(),
        virality_scorer=PayloadViralityScorer(),
        content_scorer=ContentScoreService(knowledge_query=NoOpKnowledgeQuery()),
        ab_testing_enabled=True,
        content_score_enabled=True,
    )
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="GTA 6",
        payload={
            "hook_text": "GTA 6 mudou tudo",
            "emotion": {"overall": 8},
            "script": {"title": "GTA 6", "call_to_action": "Comenta aí"},
        },
    )
    result = await service.run(ctx)
    assert "content_score_report" in result
    assert result["content_score_report"]["total_score"] > 0


def test_content_score_computed_event_registered():
    assert CONTENT_SCORE_COMPUTED in ALL_TYPES
    assert resolve_event_type("ContentScoreComputed") == CONTENT_SCORE_COMPUTED
