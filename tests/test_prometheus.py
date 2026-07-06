"""Tier E2 — Prometheus metrics export."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("JWT_SECRET", "test-secret-prometheus")
os.environ.setdefault("PROMETHEUS_METRICS_ENABLED", "true")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://contentos:contentos_secret@localhost:5432/contentos",
)

from contentos_gateway.main import app  # noqa: E402
from contentos_gateway.services.prometheus_exporter import (  # noqa: E402
    prometheus_enabled,
    prometheus_metrics_token,
    refresh_prometheus_metrics,
    render_prometheus_metrics,
)


def test_prometheus_enabled_default(monkeypatch):
    monkeypatch.delenv("PROMETHEUS_METRICS_ENABLED", raising=False)
    assert prometheus_enabled() is True
    monkeypatch.setenv("PROMETHEUS_METRICS_ENABLED", "false")
    assert prometheus_enabled() is False


def test_prometheus_token_optional(monkeypatch):
    monkeypatch.delenv("PROMETHEUS_METRICS_TOKEN", raising=False)
    assert prometheus_metrics_token() is None
    monkeypatch.setenv("PROMETHEUS_METRICS_TOKEN", "secret-token")
    assert prometheus_metrics_token() == "secret-token"


@pytest.mark.asyncio
async def test_render_prometheus_metrics_contains_series():
    await refresh_prometheus_metrics(db=None)
    body, content_type = render_prometheus_metrics()
    text = body.decode()
    assert content_type.startswith("text/plain")
    assert "contentos_cpu_percent" in text
    assert "contentos_celery_queue_depth" in text
    assert "contentos_build_info" in text


@pytest.mark.asyncio
async def test_metrics_endpoint_public():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "contentos_memory_percent" in resp.text


@pytest.mark.asyncio
async def test_metrics_endpoint_token_required(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_METRICS_TOKEN", "metrics-secret")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.get("/metrics")
        assert denied.status_code == 401
        ok = await client.get("/metrics", headers={"Authorization": "Bearer metrics-secret"})
        assert ok.status_code == 200


@pytest.mark.asyncio
async def test_metrics_endpoint_disabled(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_METRICS_ENABLED", "false")
    monkeypatch.delenv("PROMETHEUS_METRICS_TOKEN", raising=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 404
