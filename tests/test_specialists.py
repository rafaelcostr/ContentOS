"""Tests for Specialist Agents (V4.1.3 / Epic 5)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_events.domain.event_types import ALL_TYPES, SPECIALIST_SELECTED, resolve_event_type
from contentos_intelligence.application.content_intelligence_service import ContentIntelligenceService
from contentos_intelligence.application.noop import NoOpReuseAdvisor
from contentos_intelligence.application.specialists import list_specialists
from contentos_intelligence.application.specialists.context import (
    apply_specialist_to_payload,
    format_specialist_context,
)
from contentos_intelligence.application.specialists.selector import NicheSpecialistSelector
from contentos_intelligence.application.viral.payload_scorer import PayloadViralityScorer
from contentos_intelligence.domain.context import IntelligenceContext


def test_pilot_specialists_catalog():
    profiles = list_specialists()
    ids = {p.specialist_id for p in profiles}
    assert {"gaming", "technology", "business", "general"}.issubset(ids)


@pytest.mark.asyncio
async def test_selector_picks_gaming_for_gta_topic():
    selector = NicheSpecialistSelector()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="GTA 6 gameplay secrets and easter eggs",
        payload={"niche": "games"},
    )
    selection = await selector.select(ctx)
    assert selection.specialist.specialist_id == "gaming"
    assert selection.confidence >= 0.5


@pytest.mark.asyncio
async def test_selector_picks_technology_for_ai_topic():
    selector = NicheSpecialistSelector()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="ChatGPT e inteligência artificial no trabalho",
        payload={},
    )
    selection = await selector.select(ctx)
    assert selection.specialist.specialist_id == "technology"


@pytest.mark.asyncio
async def test_selector_picks_business_for_marketing_topic():
    selector = NicheSpecialistSelector()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="Funil de vendas B2B com ROI alto",
        payload={},
    )
    selection = await selector.select(ctx)
    assert selection.specialist.specialist_id == "business"


@pytest.mark.asyncio
async def test_selector_forced_specialist_id():
    selector = NicheSpecialistSelector()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="random topic",
        payload={"specialist_id": "business"},
    )
    selection = await selector.select(ctx)
    assert selection.specialist.specialist_id == "business"
    assert selection.confidence == 1.0


@pytest.mark.asyncio
async def test_selector_defaults_general_on_weak_signal():
    selector = NicheSpecialistSelector()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="olá mundo",
        payload={},
    )
    selection = await selector.select(ctx)
    assert selection.specialist.specialist_id == "general"


def test_format_specialist_context_includes_tone():
    profiles = list_specialists()
    gaming = next(p for p in profiles if p.specialist_id == "gaming")
    text = format_specialist_context(gaming)
    assert "Gaming" in text
    assert "Tom:" in text


def test_apply_specialist_to_payload():
    profiles = list_specialists()
    gaming = next(p for p in profiles if p.specialist_id == "gaming")
    from contentos_intelligence.domain.specialist import SpecialistSelection

    selection = SpecialistSelection(specialist=gaming, confidence=0.9, reason="test")
    updated = apply_specialist_to_payload({}, selection)
    assert updated["specialist_id"] == "gaming"
    assert updated["specialist_context"]
    assert updated["niche"] == "gaming"


@pytest.mark.asyncio
async def test_content_intelligence_includes_specialist_selection():
    from contentos_intelligence.application.content_score.service import ContentScoreService

    service = ContentIntelligenceService(
        reuse_advisor=NoOpReuseAdvisor(),
        virality_scorer=PayloadViralityScorer(),
        content_scorer=ContentScoreService(),
        specialist_selector=NicheSpecialistSelector(),
        ab_testing_enabled=True,
        content_score_enabled=True,
        specialist_selection_enabled=True,
    )
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="Minecraft speedrun world record",
        payload={"hook_text": "Ninguém esperava isso", "script": {"title": "Minecraft"}},
    )
    result = await service.run(ctx)
    assert "specialist_selection" in result
    assert result["specialist_selection"]["specialist"]["specialist_id"] == "gaming"


def test_specialist_selected_event_registered():
    assert SPECIALIST_SELECTED in ALL_TYPES
    assert resolve_event_type("SpecialistSelected") == SPECIALIST_SELECTED
