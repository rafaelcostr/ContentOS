"""V5.4.2 — Performance Learning tests."""

from __future__ import annotations

import pytest
from contentos_intelligence.application.performance_learning.pipeline_feedback import (
    build_pipeline_performance_feedback,
)
from contentos_intelligence.application.performance_learning.scoring import (
    build_learnings,
    classify_tier,
    compute_ctr,
    match_retention,
    topic_from_title,
)
from contentos_intelligence.domain.performance_learning import PerformanceMediaInsight


def test_compute_ctr_from_engagement_rate():
    assert compute_ctr({"engagement_rate": 0.065, "views": 1000}) == pytest.approx(0.065)


def test_compute_ctr_from_interactions():
    ctr = compute_ctr({"views": 1000, "likes": 40, "comments": 10, "shares": 5})
    assert ctr == pytest.approx(0.055)


def test_classify_tier_high():
    assert classify_tier(ctr=0.05, views=100, retention_pct=60) == "high"


def test_classify_tier_low():
    assert classify_tier(ctr=0.01, views=5, retention_pct=20) == "low"


def test_topic_from_title():
    assert topic_from_title("GTA 6 — hype #1") == "GTA 6"


def test_match_retention_by_topic():
    data = match_retention("GTA 6 review", {"gta 6": {"completion_pct": 70}})
    assert data is not None
    assert data["completion_pct"] == 70


def test_build_learnings_high_performer():
    insight = PerformanceMediaInsight(
        platform="youtube",
        external_media_id="v1",
        title="Test",
        topic="Test",
        views=500,
        ctr=0.08,
        performance_tier="high",
        hook_text="Hook forte",
    )
    lines = build_learnings(insight)
    assert any("Hook vencedor" in line for line in lines)


def test_performance_learning_enabled():
    from contentos_intelligence.application.performance_learning import performance_learning_enabled

    assert isinstance(performance_learning_enabled(), bool)


def test_build_pipeline_performance_feedback_from_publication():
    feedback = build_pipeline_performance_feedback(
        {
            "publication": {
                "platforms": {
                    "youtube": {
                        "status": "published",
                        "video_id": "yt-1",
                        "url": "https://video.example/yt-1",
                        "views": 1000,
                        "likes": 80,
                        "comments": 10,
                        "shares": 5,
                    },
                    "tiktok": {"status": "failed", "views": 250, "likes": 20},
                }
            },
            "content_score_report": {"total_score": 91},
            "retention_report": {"completion_pct": 67},
        }
    )
    assert feedback["learning_ready"] is True
    assert feedback["total_views"] == 1250
    assert feedback["total_engagement"] == 115
    assert feedback["published_count"] == 1
    assert feedback["failed_count"] == 1
    assert feedback["best_platform"] == "youtube"
    assert feedback["signals"]["content_score"] == 91.0
    assert feedback["signals"]["retention_pct"] == 67.0
