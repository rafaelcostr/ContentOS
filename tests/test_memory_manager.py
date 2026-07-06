"""Tests for Memory Manager."""

from uuid import uuid4

from contentos_memory.domain.project_memory import ProjectMemoryData


def test_format_context_full():
    memory = ProjectMemoryData(
        project_id=uuid4(),
        niche="games",
        tone="casual e direto",
        hook_style="pergunta chocante",
        goal="viralizar no TikTok",
        cta="Siga para mais",
        avg_duration=45.0,
        vocabulary=["hype", "insano", "viral"],
        style={"visual": "neon", "ritmo": "rápido"},
        history=[{"summary": "Vídeo sobre GTA 6 teve 10k views"}],
        pace="fast",
        narrator_persona="hype gamer",
    )
    ctx = memory.format_context()
    assert "games" in ctx
    assert "casual" in ctx
    assert "GTA 6" in ctx
    assert "hype gamer" in ctx
    assert ctx.endswith(".")


def test_format_context_empty():
    memory = ProjectMemoryData.empty(uuid4())
    assert memory.format_context() == ""


def test_from_dict_roundtrip():
    pid = uuid4()
    data = ProjectMemoryData(
        project_id=pid,
        niche="tech",
        tone="profissional",
        vocabulary=["IA", "automação"],
    )
    restored = ProjectMemoryData.from_dict(pid, data.to_dict())
    assert restored.niche == "tech"
    assert restored.vocabulary == ["IA", "automação"]
