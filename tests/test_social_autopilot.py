from contentos_growth.application.social_autopilot import build_social_autopilot_plan


def test_social_autopilot_defaults_to_assisted_plan() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
        channels=[{"channel_id": "ch-1", "platform": "youtube", "name": "Main", "has_credentials": True}],
        calendar_items=[
            {
                "id": "cal-1",
                "project_id": "project-1",
                "title": "GTA 6 detalhes",
                "status": "planned",
                "metadata": {"platform": "youtube", "content_type": "short"},
            }
        ],
    )

    data = plan.to_dict()

    assert data["mode"] == "assisted"
    assert data["status"] == "assisted"
    assert data["operations"]
    assert data["operations"][0]["execution"]["delegate_to"] in {"Publisher", "Growth Execution"}
    assert data["publisher_contract"]["uses_existing_publisher"] is True


def test_social_autopilot_blocks_live_without_authorization() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
        mode="live",
        publish_authorized=False,
        channels=[{"channel_id": "ch-1", "platform": "youtube", "name": "Main", "has_credentials": True}],
        calendar_items=[{"id": "cal-1", "title": "Tema", "metadata": {"platform": "youtube", "content_type": "post"}}],
    )

    assert plan.status == "blocked"
    assert plan.blocked_operations
    assert "autorização" in (plan.blocked_operations[0].block_reason or "")


def test_social_autopilot_allows_live_with_oauth_provider_and_authorization() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
        mode="live",
        publish_authorized=True,
        channels=[{"channel_id": "ch-1", "platform": "youtube", "name": "Main", "has_credentials": True}],
        calendar_items=[{"id": "cal-1", "title": "Tema", "metadata": {"platform": "youtube", "content_type": "post"}}],
    )

    assert plan.status == "ready"
    assert plan.operations
    assert not plan.blocked_operations
    assert plan.operations[0].execution["publish_mode"] == "live"


def test_social_autopilot_uses_performance_and_community_signals() -> None:
    plan = build_social_autopilot_plan(
        project_id="project-1",
        channels=[{"channel_id": "ch-1", "platform": "tiktok", "name": "TikTok", "has_credentials": True}],
        performance_rows=[{"platform": "tiktok", "title": "Vencedor", "performance_tier": "high"}],
        community_signals={"video_ideas": [{"title": "Pedido da comunidade", "detail": "Parte 2", "priority": "high"}]},
        max_operations=5,
    )

    kinds = {item.kind for item in plan.operations}

    assert "repost" in kinds
    assert "derived_video" in kinds
    assert "community_post" in kinds

