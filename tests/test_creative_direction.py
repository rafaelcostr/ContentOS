from contentos_autopilot.creative import build_creative_direction_brief
from contentos_autopilot.media import build_media_strategy_plan
from contentos_growth.application.content_factory_bridge import build_growth_context_json


def test_creative_direction_brief_composes_strategy_inputs() -> None:
    media_strategy = build_media_strategy_plan(
        topic="10 detalhes escondidos do GTA 6",
        platform="youtube",
        content_type="short",
        visual_patterns={"pacing": "fast", "colors": ["black", "red"], "movements": ["zoom-in"]},
    )
    brief = build_creative_direction_brief(
        topic="10 detalhes escondidos do GTA 6",
        objective="Aumentar retenção com curiosidades",
        platform="youtube",
        content_type="short",
        brand_dna={"brand_identity": {"tone": "curioso"}},
        audience={"description": "fãs de games"},
        media_strategy=media_strategy,
        market_opportunity={"priority": "high", "trend_brief": {"patterns": ["mistério no começo"]}},
    )

    data = brief.to_dict()
    assert data["creative_angle"] == "mystery_reveal"
    assert data["scene_brief"]["movement"] == "zoom-in"
    assert data["thumbnail_brief"]["overlay_text_max_chars"] == 25
    assert data["voice_brief"]["tone"] == "curioso"
    assert data["editor_brief"]["subtitle_style"]["avoid_full_screen_blocks"] is True
    assert data["inputs"]["has_media_strategy"] is True


def test_growth_context_passes_creative_direction_to_factory() -> None:
    creative_direction = build_creative_direction_brief(
        topic="carros de luxo",
        objective="Gerar interesse e retenção",
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
                "creative_direction": creative_direction,
            },
        }
    )

    assert context["creative_direction"]["topic"] == "carros de luxo"
    assert context["creative_direction"]["editor_brief"]["use_progress_bar"] is True
