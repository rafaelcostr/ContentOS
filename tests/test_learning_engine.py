"""Tests for Learning Engine (V4.2.3 / Epic 7)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_events.domain.event_types import ALL_TYPES, LEARNING_RECORDED, resolve_event_type
from contentos_intelligence.application.learning.extractor import extract_hook, extract_signals
from contentos_intelligence.application.learning.memory_applier import apply_to_memory
from contentos_intelligence.application.learning.service import LearningEngine
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.learning import LearningReport
from contentos_memory.domain.project_memory import ProjectMemoryData
from contentos_shared.enums import AsyncAgentStep
from contentos_shared.workflow_templates import get_builtin


def test_extract_hook_from_ab_winner():
    hook = extract_hook(
        {
            "ab_test": {"winners": {"hook": {"text": "Você não vai acreditar nisso"}}},
            "script": {"hook": "fallback"},
        }
    )
    assert hook == "Você não vai acreditar nisso"


def test_extract_signals_includes_scores_and_prompts():
    signals = extract_signals(
        {
            "topic": "IA",
            "script": {"hook": "Pare tudo", "call_to_action": "Comenta AI"},
            "content_score_report": {"total_score": 72},
            "viral_report": {"viral_score": 7.8},
            "specialist_selection": {
                "specialist_id": "technology",
                "specialist": {"name": "Technology"},
                "specialist_context": "Tom técnico",
            },
            "prompts_used": {"script": "v3", "hook": "v2"},
        }
    )
    types = {s.signal_type for s in signals}
    assert "hook" in types
    assert "cta" in types
    assert "specialist" in types
    assert "content_score" in types
    assert "viral_score" in types
    assert "prompt" in types


def test_apply_to_memory_when_score_high():
    memory = ProjectMemoryData.empty(uuid4())
    report = LearningReport(
        project_id=str(memory.project_id),
        pipeline_id=str(uuid4()),
        topic="Teste",
        content_score=80.0,
        viral_score=7.0,
        hook_text="Hook vencedor",
        cta_text="Segue para mais",
        signals=[],
    )
    updates = apply_to_memory(memory, report)
    assert report.memory_applied is True
    assert "hook_patterns" in updates
    assert "Hook vencedor" in memory.hook_patterns
    assert memory.cta == "Segue para mais"
    assert len(memory.history) == 1


def test_apply_to_memory_skips_low_score():
    memory = ProjectMemoryData.empty(uuid4())
    report = LearningReport(
        project_id=str(memory.project_id),
        pipeline_id=str(uuid4()),
        topic="Baixo",
        content_score=30.0,
        viral_score=3.0,
        hook_text="Hook fraco",
        cta_text="CTA",
        signals=[],
    )
    updates = apply_to_memory(memory, report)
    assert updates == []
    assert report.memory_applied is False
    assert memory.hook_patterns == []


def test_learning_engine_process(monkeypatch):
    monkeypatch.setenv("LEARNING_AUTO_APPLY_MEMORY", "false")
    monkeypatch.setenv("LEARNING_AUTO_INDEX_KB", "false")

    saved: list[LearningReport] = []

    def _fake_save(report: LearningReport) -> None:
        saved.append(report)

    monkeypatch.setattr(
        "contentos_intelligence.application.learning.service.LearningRepository.save_report_sync",
        lambda self, report: _fake_save(report),
    )

    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="Gaming",
        payload={
            "script": {"hook": "3 segredos", "call_to_action": "Like"},
            "content_score_report": {"total_score": 65},
            "viral_report": {"viral_score": 7.2},
        },
    )
    report = LearningEngine().process(ctx)
    assert report.hook_text == "3 segredos"
    assert report.content_score == 65.0
    assert len(saved) == 1


def test_v4_templates_enable_learning():
    for name in ("v4-intelligence", "v4-multi-text", "v4-multi-full"):
        tpl = get_builtin(name)
        assert tpl is not None
        assert tpl["config"].get("enable_learning") is True


def test_async_agent_learning_registered():
    assert AsyncAgentStep.LEARNING.value == "learning"


def test_learning_recorded_event_registered():
    assert LEARNING_RECORDED in ALL_TYPES
    assert resolve_event_type("LearningRecorded") == LEARNING_RECORDED
