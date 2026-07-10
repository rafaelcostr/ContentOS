from contentos_growth.application.growth_readiness import build_growth_readiness


def test_growth_readiness_blocks_when_oauth_credentials_are_missing():
    report = build_growth_readiness(
        {
            "OAUTH_REDIRECT_URI": "http://localhost:8000/api/v1/oauth/callback",
            "PUBLISH_MODE": "dry_run",
        }
    )

    data = report.to_dict()

    assert data["status"] == "blocked"
    assert data["totals"]["missing"] >= 6
    assert any(platform["platform"] == "youtube" and platform["status"] == "blocked" for platform in data["platforms"])
    assert "Preencha as credenciais OAuth faltantes" in data["next_steps"][0]


def test_growth_readiness_moves_to_manual_required_when_core_credentials_exist():
    report = build_growth_readiness(
        {
            "OAUTH_REDIRECT_URI": "https://contentos.local/api/v1/oauth/callback",
            "PUBLISH_MODE": "prepare_only",
            "YOUTUBE_CLIENT_ID": "yt-client",
            "YOUTUBE_CLIENT_SECRET": "yt-secret",
            "TIKTOK_CLIENT_KEY": "tt-key",
            "TIKTOK_CLIENT_SECRET": "tt-secret",
            "META_APP_ID": "meta-app",
            "META_APP_SECRET": "meta-secret",
        }
    )

    data = report.to_dict()

    assert data["status"] == "manual_required"
    assert data["totals"]["missing"] == 0
    assert data["totals"]["manual"] >= 3
    assert all(
        platform["status"] != "blocked"
        for platform in data["platforms"]
        if platform["platform"] in {"youtube", "tiktok", "instagram"}
    )


def test_growth_readiness_marks_unsupported_platforms_as_non_blocking():
    data = build_growth_readiness({}).to_dict()

    facebook = next(platform for platform in data["platforms"] if platform["platform"] == "facebook")

    assert facebook["status"] == "manual_required"
    assert facebook["checks"][0]["status"] == "not_supported"
    assert facebook["checks"][0]["required"] is False
