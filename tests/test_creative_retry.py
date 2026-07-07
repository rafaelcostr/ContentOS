"""Tier B8 — creative auto-retry decision (ADR-006)."""

from uuid import uuid4

import pytest
from contentos_agents.handlers.auto_retry import AutoRetryAgentHandler
from contentos_shared.schemas.agent import AgentTaskInput
from contentos_workflow.engine import should_creative_retry


def test_passed_advances():
    assert should_creative_retry(passed=True, retry_count=0, max_retries=1) == "advance"


def test_failed_retries_when_budget_left():
    assert should_creative_retry(passed=False, retry_count=0, max_retries=1) == "retry"
    assert should_creative_retry(passed=False, retry_count=1, max_retries=2) == "retry"


def test_failed_exhausts_budget():
    assert should_creative_retry(passed=False, retry_count=1, max_retries=1) == "advance_exhausted"
    assert should_creative_retry(passed=False, retry_count=2, max_retries=2) == "advance_exhausted"


def test_zero_max_retries_never_retries():
    assert should_creative_retry(passed=False, retry_count=0, max_retries=0) == "advance_exhausted"


@pytest.mark.asyncio
async def test_auto_retry_handler_outputs_engine_decision_payload(monkeypatch):
    stored: list[dict] = []

    class FakeAssetManager:
        async def store(self, category, data, meta):
            stored.append({"category": category, "data": data, "meta": meta})
            return {"key": "auto_retry.json"}

    handler = AutoRetryAgentHandler()
    monkeypatch.setattr(handler, "get_asset_manager", lambda: FakeAssetManager())
    task = AgentTaskInput(
        job_id=uuid4(),
        pipeline_id=uuid4(),
        project_id=uuid4(),
        step="auto_retry",
        payload={
            "video_review": {"score": 6, "passed": False, "min_score": 8},
            "video_score": 6,
            "video_review_passed": False,
            "creative_retry_from": "script",
            "retention_passed": True,
        },
    )

    output = await handler.execute(task)

    assert output.status == "completed"
    assert output.data["auto_retry_decision"] == "engine_decides"
    assert output.data["video_review_passed"] is False
    assert output.data["creative_retry_from"] == "script"
    assert stored
