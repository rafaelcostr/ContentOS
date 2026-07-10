"""Channel registry API tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from contentos_database.models import Channel, User
from contentos_gateway.api.routes.channels import (
    ChannelCreate,
    ChannelUpdate,
    _channel_response,
    _normalize_platform,
    create_channel,
    delete_channel,
    update_channel,
)
from fastapi import HTTPException


def _fake_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="channels@test.dev",
        hashed_password="x",
        full_name="Channels",
    )


def _fake_channel(*, project_id: uuid.UUID, name: str = "Main", is_active: bool = True) -> Channel:
    channel = Channel(
        id=uuid.uuid4(),
        project_id=project_id,
        platform="youtube",
        name=name,
        credentials=None,
        is_active=is_active,
    )
    channel.created_at = datetime(2026, 7, 9, 12, 0, 0, tzinfo=timezone.utc)
    return channel


def test_normalize_platform_accepts_known_values():
    assert _normalize_platform("YouTube") == "youtube"
    assert _normalize_platform("linkedin") == "linkedin"


def test_normalize_platform_rejects_unknown():
    with pytest.raises(HTTPException) as exc:
        _normalize_platform("invalid")
    assert exc.value.status_code == 422


def test_channel_response_masks_credentials_by_default():
    channel = _fake_channel(project_id=uuid.uuid4())
    channel.credentials = {"access_token": "secret"}
    response = _channel_response(channel)
    assert response.has_credentials is True
    assert not hasattr(response, "credentials") or getattr(response, "credentials", None) is None


@pytest.mark.asyncio
async def test_create_channel_normalizes_platform(monkeypatch: pytest.MonkeyPatch):
    project_id = uuid.uuid4()
    db = AsyncMock()
    db.flush = AsyncMock()
    captured: dict = {}

    def _capture_add(channel: Channel) -> None:
        captured["channel"] = channel

    db.add = _capture_add
    monkeypatch.setattr(
        "contentos_gateway.api.routes.channels.get_accessible_project",
        AsyncMock(return_value=MagicMock(id=project_id)),
    )

    body = ChannelCreate(project_id=project_id, platform="TikTok", name="  My Channel  ")
    response = await create_channel(body, db=db, user=_fake_user())

    assert captured["channel"].platform == "tiktok"
    assert captured["channel"].name == "My Channel"
    assert response.platform == "tiktok"
    assert response.name == "My Channel"


@pytest.mark.asyncio
async def test_update_channel_updates_name(monkeypatch: pytest.MonkeyPatch):
    project_id = uuid.uuid4()
    channel = _fake_channel(project_id=project_id, name="Before")
    db = AsyncMock()
    db.flush = AsyncMock()
    monkeypatch.setattr(
        "contentos_gateway.api.routes.channels._get_accessible_channel",
        AsyncMock(return_value=channel),
    )

    response = await update_channel(
        channel.id,
        ChannelUpdate(name="After"),
        db=db,
        user=_fake_user(),
    )

    assert channel.name == "After"
    assert response.name == "After"


@pytest.mark.asyncio
async def test_update_channel_requires_fields(monkeypatch: pytest.MonkeyPatch):
    channel = _fake_channel(project_id=uuid.uuid4())
    monkeypatch.setattr(
        "contentos_gateway.api.routes.channels._get_accessible_channel",
        AsyncMock(return_value=channel),
    )

    with pytest.raises(HTTPException) as exc:
        await update_channel(channel.id, ChannelUpdate(), db=AsyncMock(), user=_fake_user())
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_update_channel_toggles_active(monkeypatch: pytest.MonkeyPatch):
    channel = _fake_channel(project_id=uuid.uuid4(), is_active=True)
    db = AsyncMock()
    db.flush = AsyncMock()
    monkeypatch.setattr(
        "contentos_gateway.api.routes.channels._get_accessible_channel",
        AsyncMock(return_value=channel),
    )

    await update_channel(channel.id, ChannelUpdate(is_active=False), db=db, user=_fake_user())
    assert channel.is_active is False


@pytest.mark.asyncio
async def test_delete_channel(monkeypatch: pytest.MonkeyPatch):
    channel = _fake_channel(project_id=uuid.uuid4())
    db = AsyncMock()
    db.delete = AsyncMock()
    monkeypatch.setattr(
        "contentos_gateway.api.routes.channels._get_accessible_channel",
        AsyncMock(return_value=channel),
    )

    await delete_channel(channel.id, db=db, user=_fake_user())
    db.delete.assert_awaited_once_with(channel)
