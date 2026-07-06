"""Tests for Model Manager."""

import pytest
from contentos_models.application.model_manager import ModelManager
from contentos_models.defaults import EDITABLE_AGENTS, default_model_for_agent
from contentos_models.domain.agent_model_config import AgentModelConfig


def test_default_model_for_research(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    defaults = default_model_for_agent("research")
    assert defaults["provider"] == "ollama"
    assert defaults["model"] == "qwen3:8b"
    assert defaults["provider_type"] == "text"


def test_model_manager_get_config_without_db():
    manager = ModelManager(cache_ttl_seconds=3600)
    cfg = manager.get_config("voice")
    assert cfg.provider == "piper"
    assert cfg.provider_type == "speech"


def test_model_manager_provider_and_model():
    manager = ModelManager(cache_ttl_seconds=3600)
    provider, model = manager.provider_and_model("subtitle")
    assert provider in ("local", "whisper")
    assert model


def test_editable_agents_subset():
    assert "research" in EDITABLE_AGENTS
    assert "editor" not in EDITABLE_AGENTS


def test_agent_model_config_to_dict():
    cfg = AgentModelConfig(agent="script", provider_type="text", provider="ollama", model="qwen2.5:7b")
    data = cfg.to_dict()
    assert data["agent"] == "script"
    assert data["model"] == "qwen2.5:7b"


@pytest.mark.asyncio
async def test_update_rejects_invalid_provider():
    manager = ModelManager()

    class FakeSession:
        pass

    with pytest.raises(ValueError, match="not allowed"):
        await manager.update_config(FakeSession(), "research", "invalid_provider", "x")
