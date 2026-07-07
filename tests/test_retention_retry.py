"""V5.2.2 — Retention-driven auto_retry (hook, take, CTA)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_agents.handlers.auto_retry import AutoRetryAgentHandler
from contentos_intelligence.application.retention.retry_policy import (
    plan_retention_retry,
    resolve_retry_from_steps,
)
from contentos_shared.schemas.agent import AgentTaskInput
from contentos_workflow.engine import _pipeline_retry_passed, should_creative_retry


def test_plan_passes_when_above_thresholds():
    plan = plan_retention_retry(
        {
            "overall_score": 80,
            "hook_retention_pct": 85,
            "completion_pct": 60,
            "weak_segments": [],
            "drop_seconds": [],
        },
        min_score=65,
        min_hook_pct=70,
        min_completion_pct=40,
    )
    assert plan.passed is True
    assert plan.retry_from == ""


def test_plan_retries_hook_on_low_hook_retention():
    plan = plan_retention_retry(
        {
            "overall_score": 50,
            "hook_retention_pct": 55,
            "completion_pct": 50,
            "weak_segments": [],
            "drop_seconds": [2],
        },
        min_score=65,
        min_hook_pct=70,
        min_completion_pct=40,
    )
    assert plan.passed is False
    assert plan.target == "hook"
    assert plan.retry_from == "hook"


def test_plan_retries_takes_on_weak_body_segment():
    plan = plan_retention_retry(
        {
            "overall_score": 58,
            "hook_retention_pct": 75,
            "completion_pct": 55,
            "weak_segments": [{"label": "body", "retention_pct": 30}],
            "drop_seconds": [8],
        },
        min_score=65,
        min_hook_pct=70,
        min_completion_pct=40,
    )
    assert plan.passed is False
    assert plan.target == "take"
    assert plan.retry_from == "takes"


def test_plan_retries_script_on_weak_cta():
    plan = plan_retention_retry(
        {
            "overall_score": 60,
            "hook_retention_pct": 78,
            "completion_pct": 30,
            "weak_segments": [{"label": "cta", "retention_pct": 20}],
            "drop_seconds": [18],
        },
        min_score=65,
        min_hook_pct=70,
        min_completion_pct=40,
    )
    assert plan.passed is False
    assert plan.target == "cta"
    assert plan.retry_from == "script"


def test_resolve_retry_from_steps_fallback():
    steps = ["research", "hook", "script", "editor", "retention", "quality"]
    assert resolve_retry_from_steps("takes", steps) == "hook"
    assert resolve_retry_from_steps("hook", steps) == "hook"
    narrow = ["research", "script", "editor"]
    assert resolve_retry_from_steps("takes", narrow) == "script"


def test_pipeline_retry_passed_combined():
    assert _pipeline_retry_passed({"video_review_passed": True, "retention_passed": True}) is True
    assert _pipeline_retry_passed({"video_review_passed": True, "retention_passed": False}) is False
    assert _pipeline_retry_passed({"video_review_passed": False, "retention_passed": True}) is False


def test_pipeline_retry_passed_retention_only():
    assert _pipeline_retry_passed({"retention_passed": False}, retention_only=True) is False
    assert _pipeline_retry_passed({"retention_passed": True}, retention_only=True) is True
    assert _pipeline_retry_passed({}, retention_only=True) is True


def test_should_creative_retry_with_retention_failure():
    assert should_creative_retry(passed=False, retry_count=0, max_retries=1) == "retry"


@pytest.mark.asyncio
async def test_auto_retry_prefers_retention_retry_from(monkeypatch):
    class FakeAssetManager:
        async def store(self, category, data, meta):
            return {"key": "auto_retry.json"}

    handler = AutoRetryAgentHandler()
    monkeypatch.setattr(handler, "get_asset_manager", lambda: FakeAssetManager())
    task = AgentTaskInput(
        job_id=uuid4(),
        pipeline_id=uuid4(),
        project_id=uuid4(),
        step="auto_retry",
        payload={
            "video_review": {"score": 9, "passed": True, "min_score": 8},
            "video_review_passed": True,
            "retention_report": {
                "overall_score": 50,
                "hook_retention_pct": 55,
                "completion_pct": 50,
                "weak_segments": [],
                "drop_seconds": [2],
            },
            "retention_passed": False,
            "retention_retry_plan": {
                "passed": False,
                "target": "hook",
                "retry_from": "hook",
                "reason": "hook retention low",
            },
            "creative_retry_from": "hook",
        },
    )

    output = await handler.execute(task)

    assert output.data["auto_retry_decision"] == "engine_decides"
    assert output.data["retention_passed"] is False
    assert output.data["creative_retry_from"] == "hook"
    assert output.data["retention_retry_plan"]["target"] == "hook"
