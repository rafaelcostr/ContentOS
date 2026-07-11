from contentos_autopilot.media import build_media_strategy_plan
from contentos_growth.application.content_factory_bridge import build_growth_context_json


def test_media_strategy_prefers_gameplay_for_game_topics() -> None:
    plan = build_media_strategy_plan(
        topic="10 detalhes escondidos do GTA 6",
        platform="youtube",
        content_type="short",
        channel_twin={"identity": {"niche": "games"}},
    )

    data = plan.to_dict()
    assert data["style"] == "gameplay_documentary"
    assert any(item["source"] == "gameplay" for item in data["source_mix"])
    assert data["asset_collector_policy"]["min_duration_seconds"] == 30
    assert data["asset_collector_policy"]["license_required"] is True
    assert data["risk_score"] >= 0


def test_growth_context_passes_media_strategy_to_factory() -> None:
    media_strategy = build_media_strategy_plan(
        topic="carros de luxo",
        platform="tiktok",
        content_type="reel",
    ).to_dict()
    context = build_growth_context_json(
        calendar_item={
            "project_id": "project-1",
            "channel_id": "channel-1",
            "title": "carros de luxo",
            "metadata": {
                "platform": "tiktok",
                "content_type": "reel",
                "media_strategy": media_strategy,
            },
        }
    )

    assert context["media_strategy"]["topic"] == "carros de luxo"
    assert context["media_strategy"]["asset_search_filters"]["query"] == "carros de luxo"
    assert context["media_strategy"]["editor_hints"]["prefer_zoom_cuts"] is True
