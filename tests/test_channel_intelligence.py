from __future__ import annotations

from contentos_growth.application.channel_intelligence import build_channel_intelligence_snapshot
from contentos_growth.domain import ChannelProfile, CompetitorProfile, GrowthRecommendation, GrowthStrategy


def test_channel_intelligence_builds_high_confidence_snapshot():
    channel = ChannelProfile(
        channel_id="channel-1",
        project_id="project-1",
        platform="youtube",
        name="Canal GTA",
        score=84.0,
        has_credentials=True,
        profile={"niche": "GTA 6", "audience": "gamers brasileiros", "posting_gap_days": 3},
    )
    competitor = CompetitorProfile(
        id="competitor-1",
        project_id="project-1",
        platform="youtube",
        handle="@rival",
        display_name="Rival GTA",
        metrics={
            "analysis": {
                "patterns": {
                    "top_hooks": ["Ninguém percebeu esse detalhe"],
                    "hashtags": ["#gta6"],
                    "best_posting_hours": [18, 21],
                    "posting_gap_days": 2.5,
                }
            }
        },
    )

    snapshot = build_channel_intelligence_snapshot(
        channel=channel,
        brand={
            "niche": "GTA 6",
            "target_audience": "fãs de GTA e jogos mundo aberto",
            "tone": "curioso",
            "visual_style": {"pace": "rápido"},
            "color_palette": {"primary": "#7c3aed"},
        },
        channel_memory={
            "top_hooks": ["A Rockstar escondeu isso"],
            "top_ctas": ["comenta qual detalhe você viu"],
            "top_themes": ["segredos", "mapa"],
            "top_hashtags": ["#gta6"],
            "best_posting_hours": [19],
            "winning_videos": [{"title": "10 detalhes escondidos"}],
        },
        performance_rows=[
            {
                "platform": "youtube",
                "performance_tier": "high",
                "title": "Detalhe secreto",
                "hook_text": "Você não viu isso",
            }
        ],
        competitors=[competitor],
        strategy=GrowthStrategy(project_id="project-1", positioning="Referência em GTA 6", cadence={"posting_hours": [20]}),
        recommendations=[
            GrowthRecommendation(
                id=None,
                project_id="project-1",
                channel_id="channel-1",
                kind="hook",
                title="Reforçar curiosidade no hook",
                detail="Use mistério nos 3 primeiros segundos.",
            )
        ],
    )

    data = snapshot.to_dict()

    assert data["confidence"] == "high"
    assert data["score"] >= 75
    assert data["niche"] == "GTA 6"
    assert "A Rockstar escondeu isso" in data["content_patterns"]["top_hooks"]
    assert data["posting_intelligence"]["best_posting_hours"]
    assert "Rival GTA" in data["competitor_intelligence"]["competitors"]
    assert any("Reforçar curiosidade" in item for item in data["opportunities"])


def test_channel_intelligence_surfaces_missing_context():
    snapshot = build_channel_intelligence_snapshot(
        channel=ChannelProfile(
            channel_id="channel-1",
            project_id="project-1",
            platform="tiktok",
            name="Canal vazio",
            score=0,
            has_credentials=False,
        )
    )

    data = snapshot.to_dict()

    assert data["confidence"] == "low"
    assert data["score"] < 45
    assert any("OAuth" in risk for risk in data["risks"])
    assert any("nicho" in question.lower() for question in data["next_questions"])
