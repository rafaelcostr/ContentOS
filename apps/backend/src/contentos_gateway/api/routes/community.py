"""Community Agent API — V5.4.4 (drafts only)."""

from __future__ import annotations

from uuid import UUID

from contentos_database.models import CommunityReplyDraftRow
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.comment_analyzer import analyze_project_comments, list_comment_insights
from contentos_intelligence.application.community_agent import (
    community_agent_enabled,
    community_auto_post,
    generate_community_drafts,
    list_community_drafts,
    update_draft_status,
)
from contentos_intelligence.application.community_intelligence import build_community_intelligence_report
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



class CommunityIntelligenceResponse(BaseModel):
    project_id: str
    status: str
    summary: str
    total_comments: int = 0
    faq: list[dict] = Field(default_factory=list)
    pains: list[dict] = Field(default_factory=list)
    objections: list[dict] = Field(default_factory=list)
    requests: list[dict] = Field(default_factory=list)
    video_ideas: list[dict] = Field(default_factory=list)
    campaign_ideas: list[dict] = Field(default_factory=list)
    audience_updates: list[dict] = Field(default_factory=list)
    calendar_influence: list[dict] = Field(default_factory=list)
    objective_influence: list[dict] = Field(default_factory=list)
    reply_guardrails: list[str] = Field(default_factory=list)
    generated_at: str = ""
    comment_sync_total: int = 0
    drafts_created: int = 0

class UpdateDraftStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(draft|approved|dismissed)$")



async def _build_community_intelligence(
    db: AsyncSession,
    project_id: UUID,
    *,
    sync_comments: bool,
    generate_drafts: bool,
    persist: bool,
    max_drafts: int | None,
) -> tuple[dict, int, int]:
    comment_sync_total = 0
    drafts_created = 0
    if sync_comments:
        analysis = await analyze_project_comments(db, project_id, persist=persist)
        comment_sync_total = analysis.total_comments
    if generate_drafts:
        if community_auto_post():
            raise HTTPException(status_code=403, detail="Auto-post is not allowed for Community Intelligence")
        drafts_report = await generate_community_drafts(db, project_id, persist=persist, max_drafts=max_drafts)
        drafts_created = drafts_report.drafts_created
    insights = await list_comment_insights(db, project_id, limit=100)
    drafts = await list_community_drafts(db, project_id, status=None, limit=100)
    report = build_community_intelligence_report(
        project_id=str(project_id),
        comment_insights=insights,
        community_drafts=drafts,
    )
    return report.to_dict(), comment_sync_total, drafts_created


@router.get("/intelligence", response_model=CommunityIntelligenceResponse)
async def get_community_intelligence(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> CommunityIntelligenceResponse:
    await get_accessible_project(db, project_id, user.id)
    data, comment_sync_total, drafts_created = await _build_community_intelligence(
        db,
        project_id,
        sync_comments=False,
        generate_drafts=False,
        persist=False,
        max_drafts=None,
    )
    return CommunityIntelligenceResponse(
        **data,
        comment_sync_total=comment_sync_total,
        drafts_created=drafts_created,
    )


@router.post("/intelligence/sync", response_model=CommunityIntelligenceResponse)
async def sync_community_intelligence(
    body: GenerateDraftsRequest,
    sync_comments: bool = Query(default=True),
    generate_drafts_from_comments: bool = Query(default=True),
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> CommunityIntelligenceResponse:
    if not community_agent_enabled():
        raise HTTPException(status_code=503, detail="Community Agent disabled")
    if community_auto_post():
        raise HTTPException(status_code=403, detail="Auto-post is not allowed for Community Intelligence")
    await get_accessible_project(db, body.project_id, user.id)
    data, comment_sync_total, drafts_created = await _build_community_intelligence(
        db,
        body.project_id,
        sync_comments=sync_comments,
        generate_drafts=generate_drafts_from_comments,
        persist=body.persist,
        max_drafts=body.max_drafts,
    )
    await db.commit()
    return CommunityIntelligenceResponse(
        **data,
        comment_sync_total=comment_sync_total,
        drafts_created=drafts_created,
    )

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

