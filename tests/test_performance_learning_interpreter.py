"""Performance Learning interpreter tests — Growth OS Fase 14."""

from __future__ import annotations

from uuid import uuid4

from contentos_growth.application.performance_learning_interpreter import interpret_performance_insights


def test_interpret_empty_insights():
    result = interpret_performance_insights(str(uuid4()), [])
    assert result.total_media == 0
    assert result.recommendations
    assert result.risks


def test_interpret_high_performers():
    project_id = str(uuid4())
    rows = [
        {
            "platform": "youtube",
            "title": "Short viral hook",
            "topic": "produtividade",
            "views": 12000,
            "ctr": 0.08,
            "retention_pct": 65.0,
            "retention_delta": 5.0,
            "performance_tier": "high",
            "hook_text": "Você não vai acreditar nisso",
            "learnings": ["Hook forte nos primeiros 3s"],
        },
        {
            "platform": "tiktok",
            "title": "Vídeo fraco",
            "topic": "teste",
            "views": 200,
            "ctr": 0.01,
            "performance_tier": "low",
            "learnings": ["CTR abaixo da média"],
        },
    ]
    result = interpret_performance_insights(project_id, rows)
    assert result.total_media == 2
    assert result.high_performers == 1
    assert result.low_performers == 1
    assert result.opportunities
    assert result.top_hooks
    assert result.avg_ctr is not None
    assert any(rec.source == "performance_learning" for rec in result.recommendations)


def test_platform_breakdown():
    rows = [
        {"platform": "youtube", "views": 1000, "performance_tier": "high", "ctr": 0.05},
        {"platform": "youtube", "views": 500, "performance_tier": "medium", "ctr": 0.03},
        {"platform": "instagram", "views": 800, "performance_tier": "high", "ctr": 0.04},
    ]
    result = interpret_performance_insights(str(uuid4()), rows)
    assert len(result.platform_breakdown) == 2
    youtube = next(p for p in result.platform_breakdown if p["platform"] == "youtube")
    assert youtube["high"] == 1
