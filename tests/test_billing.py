"""Tier C3 — billing plans, credits, and Stripe helpers."""

from uuid import UUID, uuid4

import pytest
from contentos_database.billing_credits import (
    InsufficientCreditsError,
    billing_enforced,
    pipeline_credit_cost,
)
from contentos_database.billing_seed import BUILTIN_PLANS
from contentos_database.models import SubscriptionStatus
from contentos_gateway.services.billing_service import (
    STRIPE_STATUS_MAP,
    _metadata_org_id,
    stripe_enabled,
)


def test_builtin_plans_include_free():
    slugs = {p["slug"] for p in BUILTIN_PLANS}
    assert slugs == {"free", "pro", "enterprise"}
    free = next(p for p in BUILTIN_PLANS if p["slug"] == "free")
    assert free["monthly_credits"] == 50


def test_pipeline_credit_cost_default():
    assert pipeline_credit_cost() >= 1


def test_billing_enforced_default(monkeypatch):
    monkeypatch.delenv("BILLING_ENFORCE_CREDITS", raising=False)
    assert billing_enforced() is True
    monkeypatch.setenv("BILLING_ENFORCE_CREDITS", "false")
    assert billing_enforced() is False


def test_insufficient_credits_error():
    err = InsufficientCreditsError(3, 10)
    assert err.balance == 3
    assert err.required == 10
    assert "3" in str(err)


def test_stripe_status_map():
    assert STRIPE_STATUS_MAP["active"] == SubscriptionStatus.ACTIVE
    assert STRIPE_STATUS_MAP["canceled"] == SubscriptionStatus.CANCELED


def test_metadata_org_id():
    org = uuid4()
    assert _metadata_org_id({"organization_id": str(org)}) == org
    assert _metadata_org_id({}) is None
    assert _metadata_org_id({"organization_id": "not-a-uuid"}) is None


def test_stripe_enabled(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    assert stripe_enabled() is False
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    assert stripe_enabled() is True
