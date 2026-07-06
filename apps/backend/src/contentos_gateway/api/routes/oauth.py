"""OAuth routes for connecting platform channels (Tier D4)."""

from uuid import UUID

from contentos_database.models import Channel, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.oauth_service import (
    build_oauth_authorize_url,
    dashboard_oauth_redirect,
    decode_oauth_state,
    exchange_oauth_code,
)
from contentos_gateway.services.org_service import get_accessible_project
from contentos_shared.oauth_providers import SUPPORTED_OAUTH_PLATFORMS, get_oauth_config
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/oauth", tags=["OAuth"])


class OAuthStartRequest(BaseModel):
    project_id: UUID
    channel_name: str | None = None
    channel_id: UUID | None = None


class OAuthStartResponse(BaseModel):
    platform: str
    channel_id: UUID
    authorize_url: str


class OAuthPlatformInfo(BaseModel):
    platform: str
    oauth_available: bool


@router.get("/platforms", response_model=list[OAuthPlatformInfo])
async def list_oauth_platforms(_user: User = Depends(get_current_user)) -> list[OAuthPlatformInfo]:
    return [
        OAuthPlatformInfo(platform=p, oauth_available=get_oauth_config(p) is not None)
        for p in sorted(SUPPORTED_OAUTH_PLATFORMS)
    ]


@router.post("/{platform}/start", response_model=OAuthStartResponse)
async def start_oauth(
    platform: str,
    body: OAuthStartRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> OAuthStartResponse:
    platform = platform.lower()
    if platform not in SUPPORTED_OAUTH_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    await get_accessible_project(db, body.project_id, user.id)

    if body.channel_id:
        channel = await db.get(Channel, body.channel_id)
        if not channel or channel.project_id != body.project_id or channel.platform != platform:
            raise HTTPException(status_code=404, detail="Channel not found")
    else:
        channel = Channel(
            project_id=body.project_id,
            platform=platform,
            name=body.channel_name or platform.title(),
            credentials=None,
            is_active=True,
        )
        db.add(channel)
        await db.flush()

    authorize_url = build_oauth_authorize_url(
        platform=platform,
        project_id=body.project_id,
        channel_id=channel.id,
        user_id=user.id,
    )
    return OAuthStartResponse(platform=platform, channel_id=channel.id, authorize_url=authorize_url)


@router.get("/callback")
async def oauth_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    if error:
        platform = "unknown"
        return RedirectResponse(
            dashboard_oauth_redirect(platform, success=False, error=error_description or error)
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    payload = decode_oauth_state(state)
    platform = str(payload["platform"])
    channel_id = UUID(str(payload["channel_id"]))

    try:
        await exchange_oauth_code(db, platform=platform, code=code, channel_id=channel_id)
        await db.commit()
    except HTTPException as exc:
        return RedirectResponse(
            dashboard_oauth_redirect(platform, success=False, error=str(exc.detail))
        )

    return RedirectResponse(dashboard_oauth_redirect(platform, success=True))
