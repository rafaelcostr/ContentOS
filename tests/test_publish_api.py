"""Publish API routes — unit tests with dependency overrides."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("JWT_SECRET", "test-secret-publish-api")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://contentos:contentos_secret@localhost:5432/contentos",
)

from contentos_database.models import User  # noqa: E402
from contentos_gateway.api.deps import get_current_user, get_session  # noqa: E402
from contentos_gateway.main import app  # noqa: E402


def _fake_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="publish-api@test.dev",
        hashed_password="x",
        full_name="Publish API",
    )


def _fake_publication_row(
    *,
    project_id: uuid.UUID,
    platform: str = "youtube",
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.project_id = project_id
    row.pipeline_id = None
    row.platform = platform
    row.publish_mode = "dry_run"
    row.status = "dry_run"
    row.title = "Test video"
    row.external_id = None
    row.publish_url = "https://example.com/preview"
    row.error = None
    row.created_at = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)
    return row


@pytest.fixture
def project_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
async def publish_client(project_id: uuid.UUID, monkeypatch: pytest.MonkeyPatch):
    async def _noop_access(*_args, **_kwargs):
        return MagicMock(id=project_id)

    monkeypatch.setattr(
        "contentos_gateway.api.routes.publish.get_accessible_project",
        _noop_access,
    )

    async def _override_user():
        return _fake_user()

    async def _override_session():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)
        yield session

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_publish_status_returns_tri_state(publish_client: AsyncClient, project_id: uuid.UUID):
    resp = await publish_client.get(f"/api/v1/publish/status?project_id={project_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["publish_mode"] in ("dry_run", "prepare_only", "live")
    assert data["dry_run_enabled"] is True or data["live_enabled"] is True
    assert "publish_require_qa" in data
    assert isinstance(data["platforms"], list)


@pytest.mark.asyncio
async def test_publish_attempts_empty_list(publish_client: AsyncClient, project_id: uuid.UUID):
    resp = await publish_client.get(f"/api/v1/publish/attempts?project_id={project_id}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_publish_attempts_returns_rows(project_id: uuid.UUID, monkeypatch: pytest.MonkeyPatch):
    row = _fake_publication_row(project_id=project_id)

    async def _noop_access(*_args, **_kwargs):
        return MagicMock(id=project_id)

    monkeypatch.setattr(
        "contentos_gateway.api.routes.publish.get_accessible_project",
        _noop_access,
    )

    async def _override_user():
        return _fake_user()

    async def _override_session():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [row]
        session.execute = AsyncMock(return_value=result)
        yield session

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/publish/attempts?project_id={project_id}")
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 1
        assert rows[0]["platform"] == "youtube"
        assert rows[0]["publish_url"] == "https://example.com/preview"

    app.dependency_overrides.clear()
