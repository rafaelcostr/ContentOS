"""Tests for A/B Testing (V4.1.1 / Epic 6)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_events.domain.event_types import AB_VARIANT_SELECTED, ALL_TYPES, resolve_event_type
from contentos_intelligence.application.ab_testing.generators import (
    GENERATORS,
    generate_hook_variants,
)
from contentos_intelligence.application.ab_testing.scoring import score_variant
from contentos_intelligence.application.ab_testing.service import AbTestingService, apply_ab_winners_to_payload
from contentos_intelligence.application.content_intelligence_service import ContentIntelligenceService
from contentos_intelligence.domain.ab_testing import AB_DIMENSIONS, AbVariant
from contentos_intelligence.domain.context import IntelligenceContext


def test_ab_dimensions_complete():
    assert AB_DIMENSIONS == frozenset({"hook", "title", "cta", "thumbnail", "opener"})


def test_generate_hook_variants_count():
    payload = {
        "hook_text": "Você sabia disso sobre GTA 6?",
        "selected_hook": {"hook_text": "Você sabia disso sobre GTA 6?", "style": "curiosity"},
        "topic": "GTA 6",
    }
    variants = generate_hook_variants(payload)
    assert len(variants) == 3
    assert all(isinstance(v, AbVariant) and v.value for v in variants)


def test_generators_cover_all_dimensions():
    assert set(GENERATORS.keys()) == set(AB_DIMENSIONS)


def test_score_variant_hook_uses_viral_report():
    variant = AbVariant(variant_id="a", value="Ninguém esperava isso no GTA 6")
    viral = {"hook_score": 80, "viral_score": 75}
    score = score_variant("hook", variant, viral)
    assert score >= 60


def test_ab_testing_service_selects_winner():
    service = AbTestingService()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="GTA 6 viral",
        payload={
            "hook_text": "Ninguém esperava isso no GTA 6",
            "selected_hook": {"hook_text": "Ninguém esperava isso no GTA 6", "style": "shock"},
            "script": {
                "title": "GTA 6 revelado",
                "call_to_action": "Siga para mais segredos",
                "full_text": "Ninguém esperava isso. O mapa é gigante.",
            },
            "topic": "GTA 6",
        },
    )
    viral_report = {"viral_score": 72, "hook_score": 78, "cta_score": 65, "retention_prediction": 70}
    report = service.run(ctx, viral_report)
    assert len(report.dimensions) == 5
    for dim in report.dimensions:
        assert dim.winner is not None
        assert dim.variants[0].score >= dim.variants[-1].score
        assert dim.dimension in report.winners


def test_apply_ab_winners_updates_payload():
    service = AbTestingService()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="Tech tips",
        payload={
            "hook_text": "Hook A",
            "script": {"title": "Title A", "call_to_action": "CTA A"},
        },
    )
    report = service.run(ctx, {"viral_score": 60, "hook_score": 60, "cta_score": 60, "retention_prediction": 60})
    updated = apply_ab_winners_to_payload(dict(ctx.payload), report)
    assert updated.get("hook_text")
    assert updated.get("script", {}).get("title")
    assert "ab_test" in updated


@pytest.mark.asyncio
async def test_content_intelligence_includes_ab_test():
    from contentos_intelligence.application.noop import NoOpReuseAdvisor
    from contentos_intelligence.application.viral.payload_scorer import PayloadViralityScorer

    service = ContentIntelligenceService(
        reuse_advisor=NoOpReuseAdvisor(),
        virality_scorer=PayloadViralityScorer(),
        ab_testing_enabled=True,
    )
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="GTA 6",
        payload={
            "hook_text": "GTA 6 mudou tudo",
            "script": {"title": "GTA 6", "call_to_action": "Comenta aí"},
        },
    )
    result = await service.run(ctx)
    assert "ab_test" in result
    assert len(result["ab_test"]["dimensions"]) == 5


def test_ab_variant_selected_event_registered():
    assert AB_VARIANT_SELECTED in ALL_TYPES
    assert resolve_event_type("AbVariantSelected") == AB_VARIANT_SELECTED
