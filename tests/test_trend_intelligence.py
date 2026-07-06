"""Tier B9 — Trend Intelligence agent."""

from uuid import uuid4

from contentos_events.domain.event import DomainEvent
from contentos_events.domain.event_types import STEP_TO_DOMAIN_EVENT, TREND_INTELLIGENCE_FINISHED
from contentos_shared.enums import PipelineStep
from contentos_shared.trend_intelligence import build_trend_brief, format_trend_context
from contentos_shared.workflow_templates import get_builtin


def test_build_trend_brief_from_memory():
    brief = build_trend_brief(
        topic="GTA 6",
        niche="games",
        memory={
            "hook_style": "choque",
            "tone": "informal",
            "vocabulary": ["mapa", "rumor"],
            "history": [{"summary": "Vídeos com pergunta no gancho performaram bem"}],
        },
        insights=[],
    )
    assert brief["pacing_hint"]
    assert any("choque" in p.lower() or "Gancho" in p for p in brief["patterns"])
    assert "memory" in brief["sources"]
    assert "gameplay" in brief["keywords"] or brief["keywords"]


def test_build_trend_brief_from_analytics():
    brief = build_trend_brief(
        topic="Tech review",
        memory={},
        insights=[
            {
                "score": 85,
                "analysis": {
                    "score": 85,
                    "strengths": ["Gancho nos 2 primeiros segundos"],
                    "suggestions": ["Usar comparação direta"],
                    "weaknesses": ["CTA fraco"],
                    "recommended_prompt_tweaks": [{"hook_style": "pergunta"}],
                },
                "metrics": {"title": "iPhone vs Android"},
            }
        ],
    )
    assert "analytics" in brief["sources"]
    assert "pergunta" in brief["recommended_hooks"]
    assert any("Gancho" in p or "comparação" in p.lower() for p in brief["patterns"])


def test_build_trend_brief_defaults_when_empty():
    brief = build_trend_brief(topic="Tema genérico", memory={}, insights=[])
    assert brief["sources"] == ["default"]
    assert len(brief["patterns"]) >= 3
    ctx = format_trend_context(brief)
    assert "Padrões virais" in ctx


def test_v3_quality_starts_with_trend_intelligence():
    tpl = get_builtin("v3-quality")
    assert tpl is not None
    steps = tpl["steps"]
    assert steps[0] == "trend_intelligence"
    assert steps[1] == "research"
    assert len(steps) == 16
    assert tpl["config"]["enable_trend_intelligence"] is True
    assert [s.value for s in PipelineStep.v3_quality_ordered()] == steps


def test_trend_intelligence_domain_event():
    assert STEP_TO_DOMAIN_EVENT["trend_intelligence"] == TREND_INTELLIGENCE_FINISHED
    event = DomainEvent.from_agent_callback(
        step="trend_intelligence",
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        status="completed",
    )
    assert event.event_type == TREND_INTELLIGENCE_FINISHED
