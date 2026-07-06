"""Tests for Trend Forecast (V4.2.4 / Epic 10)."""

from __future__ import annotations

from uuid import uuid4

from contentos_events.domain.event_types import ALL_TYPES, TREND_FORECASTED, resolve_event_type
from contentos_intelligence.application.trend_forecast.heuristics import (
    build_production_recommendation,
    compute_expected_growth,
    compute_trend_score,
)
from contentos_intelligence.application.trend_forecast.service import TrendForecastService
from contentos_shared.trend_intelligence import build_trend_brief


def test_compute_trend_score_with_memory_and_analytics():
    brief = build_trend_brief(
        topic="GTA 6",
        niche="games",
        memory={"hook_patterns": ["pergunta", "choque"], "niche": "games"},
        insights=[{"analysis": {"score": 80}, "metrics": {"title": "Top video"}}],
    )
    score, signals = compute_trend_score(
        brief=brief,
        memory={"hook_patterns": ["pergunta", "choque"]},
        insights=[{"analysis": {"score": 80}}],
        learning_rows=[{"content_score": 70}],
        kb_entry_count=20,
    )
    assert score >= 60
    assert signals.get("analytics_avg") == 80.0
    assert signals.get("memory_boost", 0) > 0


def test_expected_growth_tiers():
    assert compute_expected_growth(80, [{"analysis": {"score": 85}}], [{"content_score": 75}]) == "very_high"
    assert compute_expected_growth(40, [], []) == "low"


def test_production_recommendation_high_score():
    text = build_production_recommendation(
        trend_score=78,
        expected_growth="high",
        brief={"pacing_hint": "rápido", "recommended_hooks": ["choque", "pergunta"]},
        topic="IA no trabalho",
    )
    assert "Produza agora" in text
    assert "IA no trabalho" in text


def test_trend_forecast_service():
    report = TrendForecastService().forecast(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="iPhone 17",
        niche="tech",
        memory={"hook_style": "curiosidade", "hook_patterns": ["vale a pena"]},
        insights=[{"analysis": {"score": 72}}],
        learning_rows=[{"content_score": 68}],
        kb_entry_count=5,
    )
    assert 0 <= report.trend_score <= 100
    assert report.expected_growth in ("low", "moderate", "high", "very_high")
    assert report.production_recommendation
    assert report.pattern_count >= 1


def test_trend_forecasted_event_registered():
    assert TREND_FORECASTED in ALL_TYPES
    assert resolve_event_type("TrendForecasted") == TREND_FORECASTED


def test_analyze_trend_uses_explicit_score():
    from contentos_intelligence.application.viral.analyzers import analyze_trend

    score = analyze_trend({"trend_score": 82, "trend_brief": {"patterns": []}})
    assert score == 82.0
