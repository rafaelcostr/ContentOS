"""OAuth token refresh for channel credentials (Tier D4)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from contentos_database.models import Channel
from contentos_shared.oauth_providers import OAuthProviderConfig, get_oauth_config


async def refresh_channel_token_if_needed(channel: Channel) -> dict[str, Any] | None:
    """Refresh OAuth token when expired; returns updated credentials or None."""
    creds = channel.credentials
    if not creds or not creds.get("refresh_token"):
        return None

    expires_at = creds.get("expires_at")
    if expires_at:
        try:
            if isinstance(expires_at, (int, float)):
                exp = datetime.fromtimestamp(float(expires_at), tz=timezone.utc)
            else:
                exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if exp > datetime.now(timezone.utc) + timedelta(minutes=5):
                return None
        except (TypeError, ValueError):
            pass

    config = get_oauth_config(channel.platform)
    if not config:
        return None

    updated = await _refresh_token(config, creds)
    if updated:
        channel.credentials = updated
    return updated


async def _refresh_token(config: OAuthProviderConfig, creds: dict[str, Any]) -> dict[str, Any] | None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        if config.platform == "tiktok":
            resp = await client.post(
                config.token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": config.client_id,
                    "client_secret": config.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": creds["refresh_token"],
                },
            )
        else:
            resp = await client.post(
                config.token_url,
                data={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": creds["refresh_token"],
                },
            )
        if resp.status_code >= 400:
            return None
        return _normalize_token_response(config.platform, resp.json(), existing=creds)


def _normalize_token_response(
    platform: str,
    data: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    creds: dict[str, Any] = dict(existing or {})
    token_block = data.get("data") if isinstance(data.get("data"), dict) else data

    access_token = token_block.get("access_token") or data.get("access_token")
    if access_token:
        creds["access_token"] = access_token

    refresh_token = token_block.get("refresh_token") or data.get("refresh_token")
    if refresh_token:
        creds["refresh_token"] = refresh_token

    expires_in = token_block.get("expires_in") or data.get("expires_in")
    if expires_in:
        creds["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

    if platform == "youtube":
        creds["privacy"] = creds.get("privacy", "private")

    return creds
