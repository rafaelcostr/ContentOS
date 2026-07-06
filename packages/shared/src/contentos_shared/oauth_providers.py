"""OAuth provider configuration for social platform publishing (Tier D4)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import urlencode

SUPPORTED_OAUTH_PLATFORMS = frozenset({"youtube", "tiktok", "instagram"})


@dataclass(frozen=True)
class OAuthProviderConfig:
    platform: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    scopes: tuple[str, ...]
    redirect_uri: str
    extra_authorize_params: dict[str, str] = field(default_factory=dict)


def oauth_redirect_uri() -> str:
    return os.getenv(
        "OAUTH_REDIRECT_URI",
        "http://localhost:8000/api/v1/oauth/callback",
    ).strip()


def get_oauth_config(platform: str) -> OAuthProviderConfig | None:
    """Return OAuth config when client credentials are set, else None."""
    platform = platform.lower()
    redirect = oauth_redirect_uri()

    if platform == "youtube":
        client_id = os.getenv("YOUTUBE_CLIENT_ID") or os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET") or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            return None
        return OAuthProviderConfig(
            platform=platform,
            client_id=client_id,
            client_secret=client_secret,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=(
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.readonly",
            ),
            redirect_uri=redirect,
            extra_authorize_params={"access_type": "offline", "prompt": "consent"},
        )

    if platform == "tiktok":
        client_id = os.getenv("TIKTOK_CLIENT_KEY") or os.getenv("TIKTOK_OAUTH_CLIENT_KEY", "")
        client_secret = os.getenv("TIKTOK_CLIENT_SECRET") or os.getenv("TIKTOK_OAUTH_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            return None
        return OAuthProviderConfig(
            platform=platform,
            client_id=client_id,
            client_secret=client_secret,
            authorize_url="https://www.tiktok.com/v2/auth/authorize/",
            token_url="https://open.tiktokapis.com/v2/oauth/token/",
            scopes=("video.upload", "video.publish"),
            redirect_uri=redirect,
        )

    if platform == "instagram":
        client_id = os.getenv("META_APP_ID") or os.getenv("INSTAGRAM_APP_ID", "")
        client_secret = os.getenv("META_APP_SECRET") or os.getenv("INSTAGRAM_APP_SECRET", "")
        if not client_id or not client_secret:
            return None
        return OAuthProviderConfig(
            platform=platform,
            client_id=client_id,
            client_secret=client_secret,
            authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
            token_url="https://graph.facebook.com/v19.0/oauth/access_token",
            scopes=(
                "instagram_basic",
                "instagram_content_publish",
                "pages_show_list",
                "pages_read_engagement",
            ),
            redirect_uri=redirect,
        )

    return None


def build_authorize_url(config: OAuthProviderConfig, state: str) -> str:
    params: dict[str, str] = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": " ".join(config.scopes),
        "state": state,
    }
    if config.platform == "tiktok":
        params["client_key"] = config.client_id
    params.update(config.extra_authorize_params)
    return f"{config.authorize_url}?{urlencode(params)}"


def list_configured_oauth_platforms() -> list[str]:
    return [p for p in sorted(SUPPORTED_OAUTH_PLATFORMS) if get_oauth_config(p) is not None]
