"""Metrics collector unit tests."""

from unittest.mock import MagicMock, patch

from contentos_gateway.services.metrics_collector import (
    AGENT_PROVIDER_MAP,
    PROVIDER_USAGE_STEPS,
    agent_model,
    collect_disk,
    collect_gpu,
)


def test_agent_model_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    provider, model = agent_model("research")
    assert provider == "ollama"
    assert model == "qwen2.5:7b"


def test_agent_model_editor():
    provider, model = agent_model("editor")
    assert provider == "ffmpeg"
    assert "1080" in model


def test_provider_usage_steps_covers_all_ai():
    all_steps = set()
    for steps in PROVIDER_USAGE_STEPS.values():
        all_steps.update(steps)
    for step in AGENT_PROVIDER_MAP:
        assert step in all_steps


def test_collect_disk():
    d = collect_disk(".")
    assert d.total_gb > 0
    assert 0 <= d.percent <= 100


def test_collect_gpu_unavailable():
    with patch("contentos_gateway.services.metrics_collector.subprocess.run", side_effect=FileNotFoundError):
        gpu = collect_gpu()
    assert gpu is not None
    assert gpu.available is False


def test_collect_gpu_available():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "NVIDIA RTX 3060, 45, 4096, 12288\n"
    with patch("contentos_gateway.services.metrics_collector.subprocess.run", return_value=mock_result):
        gpu = collect_gpu()
    assert gpu is not None
    assert gpu.available is True
    assert gpu.utilization == 45.0
