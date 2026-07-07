"""Provider factory and protocol tests."""

import pytest
from contentos_shared.plugins.registry import ContentOSPlugin, PluginMeta, PluginRegistry
from contentos_shared.providers.ai.ollama import OllamaTextProvider
from contentos_shared.providers.ai.openai import OpenAITextProvider
from contentos_shared.providers.factory import ProviderFactory
from contentos_shared.providers.protocols import SpeechProvider, SubtitleProvider, TextProvider
from contentos_shared.providers.speech.elevenlabs import ElevenLabsSpeechProvider
from contentos_shared.providers.speech.piper import PiperSpeechProvider
from contentos_shared.providers.subtitle.local_whisper import LocalWhisperProvider
from contentos_shared.providers.subtitle.openai_whisper import OpenAIWhisperProvider


def test_text_provider_ollama_direct(monkeypatch):
    monkeypatch.setenv("USE_AI_GATEWAY", "false")
    factory = ProviderFactory(text_provider="ollama")
    provider = factory.text()
    assert isinstance(provider, OllamaTextProvider)
    assert isinstance(provider, TextProvider)


def test_text_provider_openai_direct(monkeypatch):
    monkeypatch.setenv("USE_AI_GATEWAY", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    factory = ProviderFactory(text_provider="openai")
    provider = factory.text()
    assert isinstance(provider, OpenAITextProvider)


def test_speech_provider_piper_direct(monkeypatch):
    monkeypatch.setenv("USE_AI_GATEWAY", "false")
    factory = ProviderFactory(speech_provider="piper")
    provider = factory.speech()
    assert isinstance(provider, PiperSpeechProvider)
    assert isinstance(provider, SpeechProvider)


def test_speech_provider_elevenlabs_direct(monkeypatch):
    monkeypatch.setenv("USE_AI_GATEWAY", "false")
    factory = ProviderFactory(speech_provider="elevenlabs")
    provider = factory.speech()
    assert isinstance(provider, ElevenLabsSpeechProvider)


def test_subtitle_provider_local_direct(monkeypatch):
    monkeypatch.setenv("USE_AI_GATEWAY", "false")
    factory = ProviderFactory(subtitle_provider="local")
    provider = factory.subtitle()
    assert isinstance(provider, LocalWhisperProvider)
    assert isinstance(provider, SubtitleProvider)


def test_subtitle_provider_openai_direct(monkeypatch):
    monkeypatch.setenv("USE_AI_GATEWAY", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    factory = ProviderFactory(subtitle_provider="openai")
    provider = factory.subtitle()
    assert isinstance(provider, OpenAIWhisperProvider)


def test_factory_status():
    factory = ProviderFactory(text_provider="ollama", speech_provider="piper", subtitle_provider="local")
    status = factory.status()
    assert status["text"] == "ollama"
    assert status["speech"] == "piper"
    assert status["subtitle"] == "local"
    assert status["mode"] in ("direct", "ai-gateway")


def test_unknown_provider_raises_in_direct_mode(monkeypatch):
    monkeypatch.setenv("USE_AI_GATEWAY", "false")
    factory = ProviderFactory(text_provider="invalid")
    with pytest.raises(ValueError, match="Unknown TEXT_PROVIDER"):
        factory.text()


def test_ollama_config_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    provider = OllamaTextProvider()
    assert provider.base_url == "http://localhost:11434"
    assert provider.model == "qwen3:8b"


class _DummyPlugin(ContentOSPlugin):
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(name="dummy", version="0.1.0", description="test", hooks=["post_publish"])

    async def on_load(self) -> None:
        pass

    async def on_unload(self) -> None:
        pass


@pytest.mark.asyncio
async def test_plugin_registry():
    registry = PluginRegistry()
    plugin = _DummyPlugin()
    registry.register(plugin)
    assert registry.get("dummy") is plugin
    assert len(registry.list_plugins()) == 1
    assert len(registry.hook("post_publish")) == 1
    await registry.load_all()
