from __future__ import annotations

from datetime import datetime, timezone

from contentos_autopilot.temporal import build_closed_loop_cycle_policy


def test_closed_learning_temporal_builds_default_cycles() -> None:
    policy = build_closed_loop_cycle_policy(
        project_id="project-1",
        published_at="2026-07-01T00:00:00Z",
        closed_loop_report={"score": 80, "memory_updates": [{"title": "Salvar hook", "detail": "Hook vencedor"}]},
        objectives={"nodes": [{"id": "obj-1", "title": "Crescer"}]},
        now=datetime(2026, 7, 2, 1, tzinfo=timezone.utc),
    )

    data = policy.to_dict()

    assert [cycle["milestone"] for cycle in data["cycles"]] == ["24h", "48h", "7d", "30d"]
    assert data["cycles"][0]["status"] == "due"
    assert data["cycles"][1]["status"] == "scheduled"
    assert data["objective_comparison"]["status"] == "on_track"
    assert data["memory_update_proposals"][0]["requires_approval"] is True


def test_closed_learning_temporal_blocks_early_cycles_with_blockers() -> None:
    policy = build_closed_loop_cycle_policy(
        project_id="project-1",
        published_at="2026-07-01T00:00:00Z",
        closed_loop_report={"score": 20, "blockers": ["Sem analytics"]},
        objectives={"nodes": [{"id": "obj-1", "title": "Crescer"}]},
        now=datetime(2026, 7, 3, 0, tzinfo=timezone.utc),
    )

    assert policy.status == "blocked"
    assert policy.cycles[0].status == "blocked"
    assert policy.cycles[1].status == "blocked"
    assert policy.versioned_recommendations


def test_closed_learning_temporal_uses_existing_scheduler_contract() -> None:
    policy = build_closed_loop_cycle_policy(project_id="project-1")

    assert policy.scheduler_contract["uses_existing_scheduler"] is True
    assert policy.scheduler_contract["creates_scheduler_engine"] is False
    assert any("Prompts" in guardrail for guardrail in policy.guardrails)
