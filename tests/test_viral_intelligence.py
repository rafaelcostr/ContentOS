"""Tests for Viral Intelligence (V4.0.5 / Epic 1)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_intelligence.application.viral.analyzers import (
    analyze_hook,
    analyze_rhythm,
    build_recommendations,
    compute_viral_score,
)
from contentos_intelligence.application.viral.payload_scorer import PayloadViralityScorer
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import BUILTIN_TEMPLATES, get_builtin, list_builtin_names


def test_analyze_hook_strong_curiosity():
    score = analyze_hook(
        {
            "selected_hook": {"hook_text": "Você sabia disso sobre GTA?", "style": "curiosity"},
            "hook_text": "Você sabia disso sobre GTA?",
        }
    )
    assert score >= 70


def test_analyze_rhythm_ideal_scene_count():
    payload = {"scenes": [{"id": i} for i in range(6)]}
    assert analyze_rhythm(payload) >= 80


def test_compute_viral_score_weighted():
    total = compute_viral_score(
        hook_score=80,
        emotion_score=70,
        rhythm_score=85,
        scene_score=75,
        trend_score=60,
        cta_score=65,
        retention_prediction=72,
    )
    assert 60 <= total <= 100


def test_recommendations_when_scores_low():
    recs = build_recommendations(
        hook_score=50,
        emotion_score=50,
        rhythm_score=50,
        scene_score=50,
        trend_score=50,
        cta_score=40,
        retention_prediction=50,
        emotion_details={"risks": ["Intro longa"]},
    )
    assert len(recs) >= 3
    assert any("gancho" in r.lower() for r in recs)


@pytest.mark.asyncio
async def test_payload_virality_scorer_full_report():
    scorer = PayloadViralityScorer()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="GTA 6 viral",
        payload={
            "selected_hook": {"hook_text": "Ninguém esperava isso no GTA 6", "style": "shock"},
            "emotion": {"overall": 8, "retention": 7, "curiosity": 8, "emotion": 7, "impact": 8},
            "trend_context": {"patterns": ["gancho forte", "ritmo rápido"], "hook_ideas": ["pergunta"]},
            "script": {"call_to_action": "Siga para mais segredos do GTA"},
            "scenes": [{}, {}, {}, {}, {}],
        },
    )
    report = await scorer.analyze(ctx)
    assert report.viral_score >= 60
    assert report.retention_prediction > 0
    assert report.hook_score is not None
    assert isinstance(report.recommendations, list)
    d = report.to_dict()
    assert "viral_score" in d


def test_v4_intelligence_template_exists():
    assert "v4-intelligence" in BUILTIN_TEMPLATES
    tpl = get_builtin("v4-intelligence")
    assert tpl is not None
    assert len(tpl["steps"]) == 17
    assert tpl["steps"][5] == "emotion"
    assert tpl["steps"][6] == "content_intelligence"
    assert tpl["steps"][7] == "scene"
    assert tpl["config"]["enable_content_intelligence"] is True


def test_v4_intelligence_enum_order():
    steps = [s.value for s in PipelineStep.v4_intelligence_ordered()]
    assert steps.index("emotion") + 1 == steps.index("content_intelligence")
    assert len(steps) == 17


def test_list_builtin_includes_v4():
    assert "v4-intelligence" in list_builtin_names()
