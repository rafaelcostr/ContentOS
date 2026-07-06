"""Tier C4 — plan quotas."""

import pytest
from contentos_database.billing_seed import BUILTIN_PLANS
from contentos_database.quota_service import QuotaExceededError, is_unlimited, quotas_enforced


def test_builtin_plan_quotas():
    free = next(p for p in BUILTIN_PLANS if p["slug"] == "free")
    pro = next(p for p in BUILTIN_PLANS if p["slug"] == "pro")
    ent = next(p for p in BUILTIN_PLANS if p["slug"] == "enterprise")
    assert free["monthly_pipeline_quota"] == 20
    assert free["max_concurrent_pipelines"] == 1
    assert pro["max_concurrent_pipelines"] == 5
    assert ent["monthly_pipeline_quota"] == 0
    assert ent["max_concurrent_pipelines"] == 0


def test_is_unlimited():
    assert is_unlimited(0) is True
    assert is_unlimited(-1) is True
    assert is_unlimited(10) is False


def test_quotas_enforced_default(monkeypatch):
    monkeypatch.delenv("QUOTAS_ENFORCE", raising=False)
    assert quotas_enforced() is True
    monkeypatch.setenv("QUOTAS_ENFORCE", "false")
    assert quotas_enforced() is False


def test_quota_exceeded_error():
    err = QuotaExceededError("monthly_pipelines", 20, 20)
    assert err.kind == "monthly_pipelines"
    assert err.limit == 20
    assert "20" in str(err)
