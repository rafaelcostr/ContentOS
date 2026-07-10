"""Tests for Growth Report builder — Growth OS Fase 8."""

from __future__ import annotations

from uuid import uuid4

from contentos_growth.application.growth_report_builder import (
    GrowthReportSignals,
    assemble_growth_report,
    build_channel_health,
    build_risks,
    compute_growth_score,
    merge_recommendations,
)
from contentos_growth.domain import ChannelProfile, CompetitorProfile, GrowthRecommendation, GrowthStrategy


def test_compute_growth_score_with_channels_and_signals():
    channels = [
        ChannelProfile(
            channel_id="c1",
            project_id="p1",
            platform="youtube",
            name="Main",
            score=80,
            has_credentials=True,
            analyzed_at="2026-07-09",
        )
    ]
    signals = GrowthReportSignals(analytics_summary={"snapshot_count": 10}, perf_rows=[{"views": 1}])
    score = compute_growth_score(channels=channels, competitors=[], signals=signals)
    assert score >= 40


def test_build_channel_health_flags_disconnected():
    channels = [
        ChannelProfile(
            channel_id="c1",
            project_id="p1",
            platform="youtube",
            name="Offline",
            score=0,
            has_credentials=False,
        )
    ]
    health = build_channel_health(channels)
    assert health[0]["status"] == "disconnected"


def test_merge_recommendations_dedupes():
    stored = [
        GrowthRecommendation(
            id=None,
            project_id="p1",
            channel_id=None,
            kind="channel",
            title="Conectar canal",
            detail="detail",
        )
    ]
    content = [{"kind": "hook", "title": "Novo hook", "detail": "test", "confidence": "high", "source": "learning"}]
    merged = merge_recommendations(project_id="p1", stored=stored, content_recs=content)
    assert len(merged) == 2


def test_build_risks_detects_publish_failures():
    channels = []
    signals = GrowthReportSignals(publish_stats={"failed": 2, "success": 1})
    risks = build_risks(channels=channels, signals=signals)
    assert any("publicação" in risk for risk in risks)


def test_assemble_growth_report_includes_positioning():
    project_id = uuid4()
    signals = GrowthReportSignals(memory_mission="Educar sobre finanças", perf_rows=[])
    report = assemble_growth_report(
        project_id=project_id,
        channels=[],
        competitors=[],
        stored_recommendations=[],
        base_strategy=GrowthStrategy(project_id=str(project_id), goals=["Crescer no YouTube"]),
        signals=signals,
    )
    assert report.strategy
    assert report.strategy.positioning == "Educar sobre finanças"
    assert report.generated_at
    assert "Relatório consolidado" in report.summary
