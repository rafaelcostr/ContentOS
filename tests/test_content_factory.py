"""V5.3 — Content Factory tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_intelligence.application.content_factory import (
    build_batch_plan,
    factory_max_batch_size,
    pipeline_context_for_variant,
    plan_variations,
)
from contentos_intelligence.application.content_factory.variation import hook_hint_for_angle
from contentos_intelligence.domain.content_batch import BatchVariant


def test_plan_variations_rotates_angles():
    variants = plan_variations("GTA 6", 4)
    assert len(variants) == 4
    angles = [v.content_angle for v in variants]
    assert angles[0] == "hype"
    assert angles[1] == "documentary"
    assert len(set(angles)) >= 3
    assert all(v.hook_hint for v in variants)


def test_hook_hint_includes_topic():
    hint = hook_hint_for_angle("GTA 6", "tutorial", 0)
    assert "GTA 6" in hint


def test_build_batch_plan_respects_max_size(monkeypatch):
    monkeypatch.setenv("FACTORY_MAX_BATCH_SIZE", "5")
    plan = build_batch_plan("Tema", 99)
    assert plan.quantity == 5
    assert len(plan.variants) == 5


def test_build_batch_plan_require_approval_env(monkeypatch):
    monkeypatch.setenv("FACTORY_REQUIRE_APPROVAL", "true")
    plan = build_batch_plan("Tema", 2)
    assert plan.require_approval is True


def test_pipeline_context_publish_hold():
    batch_id = uuid4()
    variant = BatchVariant(index=0, topic="T", content_angle="hype", hook_hint="Hook")
    ctx = pipeline_context_for_variant(batch_id, variant, require_approval=True)
    assert ctx["factory_publish_hold"] is True
    assert ctx["factory_publish_approved"] is False
    assert ctx["content_angle"] == "hype"

    approved = pipeline_context_for_variant(batch_id, variant, require_approval=True, publish_approved=True)
    assert approved["factory_publish_hold"] is False
    assert approved["factory_publish_approved"] is True


def test_assert_can_start_batch_monthly_quota():
    pytest.importorskip("sqlalchemy")
    from contentos_database.quota_service import QuotaExceededError, assert_can_start_batch

    assert callable(assert_can_start_batch)
    assert issubclass(QuotaExceededError, Exception)


def test_content_batch_status_enum():
    from contentos_database.models import ContentBatchStatus

    assert ContentBatchStatus.PLANNED.value == "planned"
    assert ContentBatchStatus.PENDING_PUBLISH_APPROVAL.value == "pending_publish_approval"
