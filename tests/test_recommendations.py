"""Recommendation loop — phase 7.5."""

from uuid import UUID

from contentos_intelligence.application.recommendations.service import build_project_recommendations
from contentos_intelligence.domain.content_recommendation import (
    ContentRecommendation,
    ContentRecommendationReport,
)


def test_content_recommendation_report_to_dict():
    report = ContentRecommendationReport(
        project_id="p1",
        summary="ok",
        recommendations=[
            ContentRecommendation(
                kind="hook",
                title="Test",
                detail="detail",
                confidence="high",
                source="performance_learning",
            )
        ],
    )
    data = report.to_dict()
    assert data["project_id"] == "p1"
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["kind"] == "hook"


async def test_build_project_recommendations_empty_perf(monkeypatch):
    class FakeDb:
        async def get(self, model, project_id):
            class P:
                name = "Demo"
                description = "gaming"

            return P()

    async def fake_list(db, project_id, limit=50):
        return []

    async def fake_learning(db, project_id):
        return []

    async def fake_comments(db, project_id):
        return []

    monkeypatch.setattr(
        "contentos_intelligence.application.recommendations.service.list_performance_insights",
        fake_list,
    )
    monkeypatch.setattr(
        "contentos_intelligence.application.recommendations.service._load_learning_rows",
        fake_learning,
    )
    monkeypatch.setattr(
        "contentos_intelligence.application.recommendations.service._load_comment_insights",
        fake_comments,
    )

    report = await build_project_recommendations(
        FakeDb(), UUID("00000000-0000-0000-0000-000000000001")
    )
    assert "OAuth" in report.summary or report.recommendations
