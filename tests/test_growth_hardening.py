"""Growth hardening tests — Fase 18."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_growth.application.growth_hardening import (
    audit_channel_oauth,
    build_growth_health,
    classify_growth_error,
    summarize_oauth_audit,
)
from contentos_growth.infrastructure.growth_rate_limiter import GrowthRateLimiter, growth_rate_limit_enabled


def test_audit_channel_oauth_disconnected():
    audit = audit_channel_oauth(
        channel_id=str(uuid4()),
        project_id=str(uuid4()),
        platform="youtube",
        channel_name="Test",
        credentials=None,
    )
    assert audit.status == "disconnected"
    assert audit.needs_reconnect is True


def test_audit_channel_oauth_ok():
    audit = audit_channel_oauth(
        channel_id=str(uuid4()),
        project_id=str(uuid4()),
        platform="youtube",
        channel_name="Test",
        credentials={"access_token": "abc", "refresh_token": "def", "expires_at": "2099-01-01T00:00:00+00:00"},
    )
    assert audit.status == "ok"
    assert audit.needs_reconnect is False


def test_summarize_oauth_audit():
    rows = [
        audit_channel_oauth(
            channel_id="a",
            project_id="p",
            platform="youtube",
            channel_name="A",
            credentials=None,
        ),
        audit_channel_oauth(
            channel_id="b",
            project_id="p",
            platform="tiktok",
            channel_name="B",
            credentials={"access_token": "x", "refresh_token": "y", "expires_at": "2099-01-01T00:00:00+00:00"},
        ),
    ]
    summary = summarize_oauth_audit(rows)
    assert summary["total_channels"] == 2
    assert summary["needs_reconnect"] == 1


def test_build_growth_health_healthy():
    health = build_growth_health(checks={"database": True, "workflow_engine": True}, oauth_audits=[])
    assert health.status == "healthy"


def test_build_growth_health_unhealthy_db():
    health = build_growth_health(checks={"database": False, "workflow_engine": True}, oauth_audits=[])
    assert health.status == "unhealthy"


def test_classify_growth_error_rate_limit():
    failure = classify_growth_error(ValueError("Growth rate limit exceeded"))
    assert failure.kind == "rate_limit"
    assert failure.http_status == 429


def test_classify_growth_error_not_found():
    failure = classify_growth_error(ValueError("Channel not found"))
    assert failure.kind == "not_found"
    assert failure.http_status == 404


@pytest.mark.asyncio
async def test_growth_rate_limiter_allows_under_limit():
    limiter = GrowthRateLimiter()
    allowed = await limiter.check("test-user:mutate", limit=5)
    assert allowed is True


def test_growth_rate_limit_enabled_default():
    assert isinstance(growth_rate_limit_enabled(), bool)
