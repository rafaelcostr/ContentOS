"""Tier D4 — publisher live + OAuth."""

from contentos_database.channel_credentials import (
    credentials_connected,
    merge_credentials,
    token_expired,
)
from contentos_gateway.services.oauth_service import decode_oauth_state
from contentos_shared.oauth_providers import build_authorize_url, get_oauth_config, list_configured_oauth_platforms


def test_merge_credentials_db_overrides_env():
    env = {"youtube": {"access_token": "env-token", "privacy": "public"}}
    db = {"youtube": {"access_token": "oauth-token"}}
    merged = merge_credentials(env, db)
    assert merged["youtube"]["access_token"] == "oauth-token"
    assert merged["youtube"]["privacy"] == "public"


def test_credentials_connected():
    assert credentials_connected({"access_token": "abc"}) is True
    assert credentials_connected({}) is False
    assert credentials_connected(None) is False


def test_token_expired():
    assert token_expired({}) is False
    assert token_expired({"expires_at": "1999-01-01T00:00:00+00:00"}) is True


def test_get_oauth_config_missing(monkeypatch):
    monkeypatch.delenv("YOUTUBE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    assert get_oauth_config("youtube") is None


def test_get_oauth_config_youtube(monkeypatch):
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "client-id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OAUTH_REDIRECT_URI", "http://localhost:8000/api/v1/oauth/callback")
    config = get_oauth_config("youtube")
    assert config is not None
    assert config.platform == "youtube"
    url = build_authorize_url(config, "state-token")
    assert "accounts.google.com" in url
    assert "client-id" in url
    assert "state-token" in url


def test_list_configured_oauth_platforms(monkeypatch):
    monkeypatch.delenv("YOUTUBE_CLIENT_ID", raising=False)
    monkeypatch.delenv("TIKTOK_CLIENT_KEY", raising=False)
    monkeypatch.delenv("META_APP_ID", raising=False)
    assert list_configured_oauth_platforms() == []


def test_oauth_state_roundtrip(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-oauth-state")
    from contentos_gateway.config import get_settings

    get_settings.cache_clear()
    from contentos_gateway.services import oauth_service

    state = oauth_service._encode_state(
        {
            "platform": "youtube",
            "project_id": "00000000-0000-0000-0000-000000000001",
            "channel_id": "00000000-0000-0000-0000-000000000002",
            "user_id": "00000000-0000-0000-0000-000000000003",
        }
    )
    payload = decode_oauth_state(state)
    assert payload["platform"] == "youtube"
    assert payload["project_id"] == "00000000-0000-0000-0000-000000000001"
