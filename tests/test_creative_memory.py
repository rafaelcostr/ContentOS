"""V5.2.5 — Creative Memory tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_events.domain.event_types import CREATIVE_MEMORY_MERGED, STEP_TO_DOMAIN_EVENT
from contentos_intelligence.application.creative_memory import merge_creative_memory
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_shared.enums import PipelineStep


def test_merge_uses_existing_learning_report():
    report = merge_creative_memory(
        IntelligenceContext(
            project_id=uuid4(),
            pipeline_id=uuid4(),
            topic="GTA 6",
            payload={
                "learning_report": {
                    "topic": "GTA 6",
                    "hook_text": "Hook aprendido",
                    "cta_text": "CTA forte",
                    "content_score": 75,
                    "memory_applied": True,
                    "memory_updates": ["hook_patterns"],
                    "kb_indexed_count": 1,
                },
                "knowledge_base_report": {"knowledge_indexed_count": 2},
            },
        )
    )
    assert report.memory_applied is True
    assert "Hook aprendido" in report.creative_memory_context
    assert report.knowledge_indexed_count == 2
    assert report.hints["hook_hint"] == "Hook aprendido"


def test_merge_runs_learning_when_missing(monkeypatch):
    monkeypatch.setenv("LEARNING_AUTO_APPLY_MEMORY", "false")
    monkeypatch.setenv("LEARNING_AUTO_INDEX_KB", "false")
    monkeypatch.setattr(
        "contentos_intelligence.infrastructure.learning_repository.LearningRepository.save_report_sync",
        lambda self, report: None,
    )
    report = merge_creative_memory(
        IntelligenceContext(
            project_id=uuid4(),
            pipeline_id=uuid4(),
            topic="Test",
            payload={
                "script": {"hook": "Novo hook", "call_to_action": "Segue"},
                "content_score_report": {"total_score": 70},
            },
        )
    )
    assert report.learning_report.get("hook_text") == "Novo hook"
    assert report.creative_memory_context


def test_factory_full_includes_creative_memory():
    steps = PipelineStep.factory_full_ordered()
    assert len(steps) == 31
    assert steps.index(PipelineStep.KNOWLEDGE_BASE) + 1 == steps.index(PipelineStep.CREATIVE_MEMORY)
    assert steps.index(PipelineStep.CREATIVE_MEMORY) + 1 == steps.index(PipelineStep.ANALYTICS)


def test_v5_autopilot_includes_creative_memory():
    steps = PipelineStep.v5_media_autopilot_ordered()
    assert len(steps) == 18
    assert steps.index(PipelineStep.SEO) + 1 == steps.index(PipelineStep.CREATIVE_MEMORY)
    assert steps.index(PipelineStep.CREATIVE_MEMORY) + 1 == steps.index(PipelineStep.PUBLISHER)


def test_creative_memory_domain_event():
    assert STEP_TO_DOMAIN_EVENT["creative_memory"] == CREATIVE_MEMORY_MERGED


@pytest.mark.asyncio
async def test_creative_memory_agent_handler():
    from contentos_agents.handlers.creative_memory import CreativeMemoryAgentHandler
    from contentos_shared.schemas.agent import AgentTaskInput

    handler = CreativeMemoryAgentHandler()

    async def fake_store(_self, category, data, meta):
        return type("R", (), {"key": "scripts/creative_memory.json", "bucket": "contentos", "id": uuid4()})()

    handler.get_asset_manager = lambda: type("M", (), {"store": fake_store})()

    output = await handler.execute(
        AgentTaskInput(
            job_id=uuid4(),
            project_id=uuid4(),
            pipeline_id=uuid4(),
            step="creative_memory",
            payload={
                "topic": "GTA 6",
                "learning_report": {
                    "hook_text": "Hook",
                    "memory_applied": False,
                    "memory_updates": [],
                    "kb_indexed_count": 0,
                },
            },
        )
    )
    assert output.data["creative_memory_context"]
    assert output.data["creative_memory"]["topic"] == "GTA 6"
