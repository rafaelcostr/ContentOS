"""Provider health check tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from contentos_shared.providers.health import check_ollama, check_piper, check_whisper


@pytest.mark.asyncio
async def test_check_ollama_healthy(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"models": [{"name": "qwen2.5:7b"}]}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("contentos_shared.providers.health.httpx.AsyncClient", return_value=mock_client):
        result = await check_ollama()

    assert result.healthy is True
    assert result.name == "ollama"


@pytest.mark.asyncio
async def test_check_piper_unhealthy_on_error(monkeypatch):
    monkeypatch.setenv("PIPER_URL", "http://piper:5000")

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=ConnectionError("refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("contentos_shared.providers.health.httpx.AsyncClient", return_value=mock_client):
        result = await check_piper()

    assert result.healthy is False


@pytest.mark.asyncio
async def test_check_whisper_loaded(monkeypatch):
    monkeypatch.setenv("WHISPER_URL", "http://whisper:8080")

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"loaded": True, "model": "large-v3"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("contentos_shared.providers.health.httpx.AsyncClient", return_value=mock_client):
        result = await check_whisper()

    assert result.healthy is True
    assert result.detail == "large-v3"
