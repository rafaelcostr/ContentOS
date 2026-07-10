"""Gateway hardening — rate limit, timeout, readiness (V5.5.4)."""

from __future__ import annotations

import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["DEBUG"] = "true"
os.environ["JWT_SECRET"] = "test-secret-hardening-32-characters"
os.environ.setdefault("GATEWAY_RATE_LIMIT_ENABLED", "true")
os.environ.setdefault("GATEWAY_RATE_LIMIT_PER_MINUTE", "5")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://contentos:contentos_secret@localhost:5432/contentos",
)

from contentos_gateway.config import Settings  # noqa: E402
from contentos_gateway.main import app  # noqa: E402
from contentos_gateway.middleware.hardening import gateway_request_timeout_seconds  # noqa: E402
from contentos_gateway.services.gateway_rate_limiter import (  # noqa: E402
    GatewayRateLimiter,
    gateway_rate_limit_exempt_paths,
)


@pytest.mark.asyncio
async def test_health_not_rate_limited():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(10):
            resp = await client.get("/health")
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_returns_429(monkeypatch):
    from unittest.mock import AsyncMock, patch

    monkeypatch.setenv("GATEWAY_RATE_LIMIT_ENABLED", "true")
    from contentos_gateway.main import create_app

    test_app = create_app()

    @test_app.get("/_test_rate")
    async def _ping():
        return {"ok": True}

    limiter = AsyncMock()
    limiter.check = AsyncMock(side_effect=[True, True, False])

    with patch("contentos_gateway.middleware.hardening.get_gateway_rate_limiter", return_value=limiter):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/_test_rate")).status_code == 200
            assert (await client.get("/_test_rate")).status_code == 200
            assert (await client.get("/_test_rate")).status_code == 429


def test_request_timeout_config(monkeypatch):
    monkeypatch.setenv("GATEWAY_REQUEST_TIMEOUT_SECONDS", "60")
    assert gateway_request_timeout_seconds() == 60.0


def test_exempt_paths_include_health():
    paths = gateway_rate_limit_exempt_paths()
    assert "/health" in paths
    assert "/health/ready" in paths


def test_gateway_rate_limiter_in_memory(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:0/0")
    monkeypatch.setattr("contentos_gateway.services.gateway_rate_limiter.time.time", lambda: 1234567890)
    limiter = GatewayRateLimiter()

    async def _run():
        key = "test-client"
        for _ in range(3):
            await limiter.check(key, 3)
        blocked = await limiter.check(key, 3)
        return blocked

    assert asyncio.run(_run()) is False


def test_loadtest_scripts_exist():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert (root / "scripts" / "loadtest" / "k6-smoke.js").is_file()
    assert (root / "scripts" / "loadtest" / "smoke_load.py").is_file()


def test_gateway_timeout_default():
    assert gateway_request_timeout_seconds() >= 5.0


def test_production_rejects_default_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(debug=False, jwt_secret="change-me")


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(debug=False, jwt_secret="x" * 32, cors_origins="*")

