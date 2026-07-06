"""Tests for Analytics AI (V2.8)."""

from uuid import uuid4

from contentos_analytics_ai.application.analytics_service import AnalyticsService
from contentos_analytics_ai.domain.insight import AnalyticsInsightData


def test_collect_metrics_from_publication():
    svc = AnalyticsService()
    metrics = svc.collect_metrics(
        {
            "topic": "AI trends",
            "publication": {
                "title": "AI trends 2026",
                "hashtags": ["ai", "tech"],
                "platforms": {
                    "tiktok": {"views": 1200, "likes": 85},
                    "youtube": {"view_count": 500, "like_count": 40},
                },
            },
        }
    )
    assert metrics["views"] == 1700
    assert metrics["likes"] == 125
    assert metrics["source"] == "platform"
    assert metrics["title"] == "AI trends 2026"


def test_collect_metrics_estimated_when_empty():
    svc = AnalyticsService()
    metrics = svc.collect_metrics({"topic": "test"})
    assert metrics["source"] == "estimated"
    assert metrics["views"] == 0


def test_insight_data_to_dict():
    pid = uuid4()
    data = AnalyticsInsightData(
        project_id=uuid4(),
        pipeline_id=pid,
        metrics={"views": 10},
        analysis={"summary": "Good hook", "score": 78},
    )
    d = data.to_dict()
    assert d["pipeline_id"] == str(pid)
    assert d["score"] == 78
    assert d["summary"] == "Good hook"


def test_apply_to_memory_without_db():
    svc = AnalyticsService()
    # No DATABASE_URL — should fail gracefully
    result = svc.apply_to_memory(uuid4(), {"summary": "x", "suggestions": ["a"]}, uuid4())
    assert result is False
