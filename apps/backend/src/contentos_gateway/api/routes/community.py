"""Community Agent API — V5.4.4 (drafts only)."""

from __future__ import annotations

from uuid import UUID

from contentos_database.models import CommunityReplyDraftRow
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.community_agent import (
    community_agent_enabled,
    community_auto_post,
    generate_community_drafts,
    list_community_drafts,
    update_draft_status,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/community", tags=["Community Agent"])


class GenerateDraftsRequest(BaseModel):
    project_id: UUID
    persist: bool = True
    max_drafts: int | None = Field(default=None, ge=1, le=50)


class CommentReplyDraftResponse(BaseModel):
    draft_id: str | None = None
    platform: str
    external_media_id: str | None = None
    media_title: str | None = None
    original_comment: str
    comment_author: str | None = None
    draft_reply: str
    category: str
    sentiment: str
    priority: int = 0
    status: str = "draft"


class CommunityDraftReportResponse(BaseModel):
    project_id: str
    drafts: list[CommentReplyDraftResponse]
    drafts_created: int
    auto_post: bool
    summary: str


class CommunityDraftRowResponse(BaseModel):
    id: str
    project_id: str
    platform: str
    external_media_id: str | None
    media_title: str | None
    original_comment: str
    comment_author: str | None
    draft_reply: str
    category: str
    sentiment: str
    priority: int
    status: str
    created_at: str | None
    updated_at: str | None


class UpdateDraftStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(draft|approved|dismissed)$")


@router.post("/drafts/generate", response_model=CommunityDraftReportResponse)
async def generate_drafts(
    body: GenerateDraftsRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> CommunityDraftReportResponse:
    if not community_agent_enabled():
        raise HTTPException(status_code=503, detail="Community Agent disabled")
    if community_auto_post():
        raise HTTPException(status_code=403, detail="Auto-post is not allowed in V5.4.4")
    await get_accessible_project(db, body.project_id, user.id)
    report = await generate_community_drafts(
        db,
        body.project_id,
        persist=body.persist,
        max_drafts=body.max_drafts,
    )
    await db.commit()
    d = report.to_dict()
    return CommunityDraftReportResponse(
        project_id=d["project_id"],
        drafts=[CommentReplyDraftResponse(**x) for x in d["drafts"]],
        drafts_created=d["drafts_created"],
        auto_post=d["auto_post"],
        summary=d["summary"],
    )


@router.get("/drafts", response_model=list[CommunityDraftRowResponse])
async def get_drafts(
    project_id: UUID = Query(...),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[CommunityDraftRowResponse]:
    await get_accessible_project(db, project_id, user.id)
    rows = await list_community_drafts(db, project_id, status=status, limit=limit)
    return [CommunityDraftRowResponse(**row) for row in rows]


@router.patch("/drafts/{draft_id}", response_model=dict)
async def patch_draft_status(
    draft_id: UUID,
    body: UpdateDraftStatusRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> dict:
    result = await db.execute(
        select(CommunityReplyDraftRow).where(CommunityReplyDraftRow.id == draft_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Draft not found")
    await get_accessible_project(db, row.project_id, user.id)
    try:
        updated = await update_draft_status(db, draft_id, status=body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Draft not found")
    await db.commit()
    return updated
