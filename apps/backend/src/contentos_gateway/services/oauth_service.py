"""OAuth authorization flow for platform channels (Tier D4)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from contentos_database.models import Channel
from contentos_gateway.config import settings
from contentos_shared.oauth_providers import OAuthProviderConfig, build_authorize_url, get_oauth_config
from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

ALGORITHM = "HS256"
OAUTH_STATE_EXPIRE_MINUTES = 15


def _encode_state(payload: dict[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=OAUTH_STATE_EXPIRE_MINUTES)
    data = {**payload, "exp": expire, "type": "oauth_state"}
    return jwt.encode(data, settings.jwt_secret, algorithm=ALGORITHM)


def decode_oauth_state(state: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc
    if payload.get("type") != "oauth_state":
        raise HTTPException(status_code=400, detail="Invalid OAuth state type")
    return payload


def build_oauth_authorize_url(
    *,
    platform: str,
    project_id: UUID,
    channel_id: UUID,
    user_id: UUID,
) -> str:
    config = get_oauth_config(platform)
    if not config:
        raise HTTPException(
            status_code=503,
            detail=f"OAuth not configured for {platform}. Set client credentials in environment.",
        )
    state = _encode_state(
        {
            "platform": platform.lower(),
            "project_id": str(project_id),
            "channel_id": str(channel_id),
            "user_id": str(user_id),
        }
    )
    return build_authorize_url(config, state)


async def exchange_oauth_code(
    db: AsyncSession,
    *,
    platform: str,
    code: str,
    channel_id: UUID,
) -> Channel:
    config = get_oauth_config(platform)
    if not config:
        raise HTTPException(status_code=503, detail=f"OAuth not configured for {platform}")

    channel = await db.get(Channel, channel_id)
    if not channel or channel.platform.lower() != platform.lower():
        raise HTTPException(status_code=404, detail="Channel not found")

    token_data = await _exchange_code(config, code)
    credentials = _normalize_token_response(platform, token_data)

    if platform == "instagram":
        credentials = await _enrich_instagram_credentials(credentials)

    credentials["oauth_connected_at"] = datetime.now(timezone.utc).isoformat()
    channel.credentials = credentials
    await db.flush()
    return channel


async def _exchange_code(config: OAuthProviderConfig, code: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        if config.platform == "tiktok":
            resp = await client.post(
                config.token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": config.redirect_uri,
                },
            )
        else:
            resp = await client.post(
                config.token_url,
                data={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": config.redirect_uri,
                },
            )
        if resp.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {resp.text[:300]}")
        data = resp.json()
        if config.platform == "instagram" and "access_token" in data and "expires_in" not in data:
            long = await client.get(
                "https://graph.facebook.com/v19.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "fb_exchange_token": data["access_token"],
                },
            )
            if long.status_code < 400:
                data = long.json()
        return data


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

    open_id = token_block.get("open_id") or data.get("open_id")
    if open_id:
        creds["open_id"] = open_id

    if platform == "youtube":
        creds["privacy"] = creds.get("privacy", "private")

    return creds


async def _enrich_instagram_credentials(credentials: dict[str, Any]) -> dict[str, Any]:
    access_token = credentials.get("access_token")
    if not access_token:
        return credentials

    async with httpx.AsyncClient(timeout=30.0) as client:
        pages = await client.get(
            "https://graph.facebook.com/v19.0/me/accounts",
            params={"access_token": access_token, "fields": "id,name,instagram_business_account"},
        )
        if pages.status_code >= 400:
            return credentials
        for page in pages.json().get("data", []):
            ig_account = page.get("instagram_business_account")
            if ig_account and ig_account.get("id"):
                credentials["instagram_user_id"] = ig_account["id"]
                credentials["page_id"] = page.get("id")
                credentials["page_name"] = page.get("name")
                break
    return credentials


def dashboard_oauth_redirect(platform: str, *, success: bool = True, error: str | None = None) -> str:
    base = os.getenv("DASHBOARD_URL") or settings.cors_origins_list[0] if settings.cors_origins_list else "http://localhost:3000"
    base = base.rstrip("/")
    params = f"oauth={'success' if success else 'error'}&platform={platform}"
    if error:
        params += f"&message={error[:120]}"
    return f"{base}/plugins?{params}"
