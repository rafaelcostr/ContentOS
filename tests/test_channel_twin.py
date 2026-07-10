from contentos_autopilot.objectives import build_objective_tree
from contentos_autopilot.twin import build_channel_twin_snapshot


def test_channel_twin_composes_existing_read_models() -> None:
    intelligence = {
        "channel_id": "channel-1",
        "project_id": "project-1",
        "platform": "youtube",
        "name": "Canal GTA 6",
        "confidence": "high",
        "score": 86,
        "summary": "Canal GTA 6 em youtube · confiança high · score 86/100",
        "niche": "GTA 6",
        "audience": "Fas de jogos e curiosidades",
        "brand_identity": {"tone": "curioso"},
        "visual_identity": {"style": {"pace": "rapido"}},
        "content_patterns": {"top_hooks": ["Ninguem percebeu isso"]},
        "historical_videos": {"total_media": 8, "high_performers": 3, "winning_titles": ["Segredos GTA"]},
        "posting_intelligence": {"best_posting_hours": [18, 21]},
        "competitor_intelligence": {"competitors": ["Rival GTA"]},
        "strategy_context": {"goals": ["Aumentar retencao"], "cadence": {"weekly_posts": 5}},
        "risks": [],
        "opportunities": ["Replicar formato de alto desempenho."],
        "next_questions": ["Qual hook testar hoje?"],
    }
    workspace = {
        "scope": {
            "project_id": "project-1",
            "channel_id": "channel-1",
            "platform": "youtube",
            "channel_name": "Canal GTA 6",
        },
        "profile": {"channel_id": "channel-1", "project_id": "project-1", "platform": "youtube", "name": "Canal GTA 6"},
        "calendar": [{"status": "planned", "title": "10 detalhes escondidos", "objective_id": "obj-1"}],
        "learning": [{"insight": "Hooks de misterio seguram melhor"}],
        "performance": [{"performance_tier": "high", "title": "Segredos GTA"}],
        "recommendations": [{"title": "Publicar no horario 21h"}],
        "competitors": [{"handle": "@rival"}],
        "assets": [{"asset_id": "asset-1"}],
        "health_status": "healthy",
    }
    objectives = build_objective_tree(
        project_id="project-1",
        strategy=intelligence["strategy_context"],
        channels=[workspace["profile"]],
    )

    twin = build_channel_twin_snapshot(
        channel_intelligence=intelligence,
        workspace=workspace,
        objectives=objectives,
        community_rows=[{"sentiment": "positive", "text": "Quando sai mais?"}],
    )

    assert twin.status == "ready"
    assert twin.identity["niche"] == "GTA 6"
    assert twin.brand_dna["content_patterns"]["top_hooks"] == ["Ninguem percebeu isso"]
    assert twin.calendar["planned"] == 1
    assert twin.performance["high_performers"] == 3
    assert twin.community["comment_count"] == 1
    assert twin.objectives["nodes"]
    assert "Publicar no horario 21h" in twin.opportunities


def test_channel_twin_surfaces_blocked_channel_without_creating_memory() -> None:
    twin = build_channel_twin_snapshot(
        channel_intelligence={
            "channel_id": "channel-2",
            "project_id": "project-1",
            "platform": "tiktok",
            "name": "TikTok GTA",
            "confidence": "low",
            "score": 25,
            "summary": "Canal sem OAuth",
            "risks": ["Canal sem OAuth: historico e publicacao real ficam limitados."],
        },
        workspace={"health_status": "critical", "calendar": [], "learning": [], "performance": []},
    )

    assert twin.status == "blocked"
    assert twin.objectives == {"project_id": "project-1", "nodes": []}
    assert twin.resources["health_status"] == "critical"
    assert any("OAuth" in risk for risk in twin.risks)
