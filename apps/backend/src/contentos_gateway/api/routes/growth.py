"""Growth AI foundation routes."""

from __future__ import annotations

import asyncio
from uuid import UUID

import httpx
from contentos_autopilot.adapters.growth import GrowthChannelTwinProvider, GrowthMarketIntelligenceProvider
from contentos_autopilot.cost import build_cost_decision_score
from contentos_autopilot.resources import build_resource_readiness
from contentos_autopilot.temporal import build_closed_loop_cycle_policy
from contentos_autopilot.visual import build_visual_pattern_snapshot
from contentos_database.billing_credits import InsufficientCreditsError, billing_enforced, pipeline_credit_cost
from contentos_database.models import AssetMediaProfile, Channel, Pipeline, User
from contentos_database.quota_service import (
    QuotaExceededError,
    assert_can_start_pipeline,
    get_quota_status,
    is_unlimited,
    quotas_enforced,
)
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.config import settings
from contentos_gateway.services.billing_service import consume_pipeline_credit, ensure_org_billing, get_org_billing
from contentos_gateway.services.metrics_collector import collect_celery_queues, collect_system_metrics
from contentos_gateway.services.org_service import get_accessible_project
from contentos_growth import GrowthService
from contentos_growth.application.growth_hardening import classify_growth_error, summarize_oauth_audit
from contentos_growth.application.growth_readiness import build_growth_readiness
from contentos_growth.application.post_manager import is_text_content_type
from contentos_growth.application.social_approval_queue import build_social_approval_queue
from contentos_growth.application.social_autopilot import build_social_autopilot_plan
from contentos_growth.application.social_dispatcher import build_social_dispatch_plan
from contentos_growth.application.social_learning import build_social_learning_report
from contentos_growth.application.social_observability import build_social_observability_report
from contentos_growth.domain import GrowthRecommendation
from contentos_growth.infrastructure.growth_rate_limiter import assert_growth_rate_limit
from contentos_growth.infrastructure.sqlalchemy_repository import SqlAlchemyGrowthRepository
from contentos_growth.platform_registry import list_growth_platforms
from contentos_intelligence.application.comment_analyzer import list_comment_insights
from contentos_intelligence.application.community_agent import list_community_drafts
from contentos_intelligence.application.community_intelligence import build_community_intelligence_report
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/growth", tags=["Growth"])


async def _enforce_growth_rate_limit(user: User, action: str = "mutate") -> None:
    try:
        await assert_growth_rate_limit(str(user.id), action)
    except ValueError as exc:
        failure = classify_growth_error(exc)
        raise HTTPException(status_code=failure.http_status, detail=failure.to_dict()) from exc


def _growth_error_response(exc: Exception) -> HTTPException:
    failure = classify_growth_error(exc)
    return HTTPException(status_code=failure.http_status, detail=failure.to_dict())


class GrowthHealthResponse(BaseModel):
    status: str
    checks: dict = Field(default_factory=dict)
    summary: str = ""
    oauth_issues: int = 0
    generated_at: str = ""


class GrowthOAuthAuditResponse(BaseModel):
    total_channels: int
    by_status: dict = Field(default_factory=dict)
    needs_reconnect: int
    channels: list[dict] = Field(default_factory=list)


class GrowthReadinessResponse(BaseModel):
    status: str
    summary: str
    generated_at: str
    totals: dict = Field(default_factory=dict)
    global_checks: list[dict] = Field(default_factory=list)
    platforms: list[dict] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class GrowthAutopilotStatusResponse(BaseModel):
    project_id: str
    mode: str
    status: str
    summary: str
    score: int
    generated_at: str
    stages: list[dict] = Field(default_factory=list)
    channels: list[dict] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class GrowthAutonomousExecutionPlanResponse(BaseModel):
    project_id: str
    mode: str
    status: str
    summary: str
    actions: list[dict] = Field(default_factory=list)
    blocked_actions: list[dict] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    generated_at: str = ""


class GrowthClosedLoopResponse(BaseModel):
    project_id: str
    status: str
    summary: str
    score: int
    learned: list[str] = Field(default_factory=list)
    strategy_updates: list[dict] = Field(default_factory=list)
    calendar_updates: list[dict] = Field(default_factory=list)
    execution_updates: list[dict] = Field(default_factory=list)
    memory_updates: list[dict] = Field(default_factory=list)
    next_cycle: dict = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    generated_at: str = ""



class ResourceReadinessResponse(BaseModel):
    status: str
    score: int
    execution_window: str
    summary: str
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    gpu_available: bool = False
    gpu_utilization: float | None = None
    queue_pending: int = 0
    workers: int = 0
    blockers: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    generated_at: str = ""


class ClosedLoopTemporalResponse(BaseModel):
    project_id: str
    status: str
    summary: str
    cycles: list[dict] = Field(default_factory=list)
    objective_comparison: dict = Field(default_factory=dict)
    versioned_recommendations: list[dict] = Field(default_factory=list)
    memory_update_proposals: list[dict] = Field(default_factory=list)
    scheduler_contract: dict = Field(default_factory=dict)
    guardrails: list[str] = Field(default_factory=list)
    generated_at: str = ""
    recommendations_saved: int = 0


class SocialAutopilotPlanResponse(BaseModel):
    project_id: str
    mode: str
    status: str
    summary: str
    operations: list[dict] = Field(default_factory=list)
    blocked_operations: list[dict] = Field(default_factory=list)
    publisher_contract: dict = Field(default_factory=dict)
    scheduler_contract: dict = Field(default_factory=dict)
    governance_contract: dict = Field(default_factory=dict)
    audit_log: list[dict] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    generated_at: str = ""


class SocialApprovalQueueResponse(BaseModel):
    project_id: str
    status: str
    summary: str
    items: list[dict] = Field(default_factory=list)
    publisher_contract: dict = Field(default_factory=dict)
    scheduler_contract: dict = Field(default_factory=dict)
    generated_at: str = ""

class SocialDispatchPlanResponse(BaseModel):
    project_id: str
    status: str
    summary: str
    commands: list[dict] = Field(default_factory=list)
    skipped_items: list[dict] = Field(default_factory=list)
    execution_contract: dict = Field(default_factory=dict)
    generated_at: str = ""

class SocialObservabilityResponse(BaseModel):
    project_id: str
    status: str
    readiness_score: int
    summary: str
    counts: dict = Field(default_factory=dict)
    manual_actions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    lifecycle: dict = Field(default_factory=dict)
    audit_events: list[dict] = Field(default_factory=list)
    generated_at: str = ""

class SocialLearningResponse(BaseModel):
    project_id: str
    status: str
    score: int
    summary: str
    learned: list[str] = Field(default_factory=list)
    recommendations: list[dict] = Field(default_factory=list)
    memory_candidates: list[dict] = Field(default_factory=list)
    next_cycle: dict = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    generated_at: str = ""
class CostDecisionResponse(BaseModel):
    status: str
    mode: str
    quantity: int
    credit_cost_per_pipeline: int
    total_credit_cost: int
    credits_balance: int | None = None
    credits_ok: bool
    monthly_quota: int
    monthly_used: int
    monthly_remaining: int | None = None
    concurrent_limit: int
    concurrent_active: int
    quota_ok: bool
    cost_score: int
    estimated_ai_cost_units: int
    recommendations: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    generated_at: str = ""


@router.get("/health", response_model=GrowthHealthResponse)
async def get_growth_health(
    project_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GrowthHealthResponse:
    if project_id is not None:
        await get_accessible_project(db, project_id, user.id)
    external_checks: dict[str, bool] = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.workflow_engine_url.rstrip('/')}/health")
            external_checks["workflow_engine"] = resp.status_code < 500
    except Exception:
        external_checks["workflow_engine"] = False
    health = await _growth_service(db).get_growth_health(
        db,
        project_id,
        external_checks=external_checks,
    )
    return GrowthHealthResponse(**health.to_dict())


@router.get("/readiness", response_model=GrowthReadinessResponse)
async def get_growth_readiness(
    user: User = Depends(get_current_user),
) -> GrowthReadinessResponse:
    _ = user
    return GrowthReadinessResponse(**build_growth_readiness().to_dict())


@router.get("/autopilot/status", response_model=GrowthAutopilotStatusResponse)
async def get_growth_autopilot_status(
    project_id: UUID,
    mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    horizon_days: int = Query(default=30, ge=1, le=90),
    timezone: str = Query(default="UTC"),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GrowthAutopilotStatusResponse:
    await get_accessible_project(db, project_id, user.id)
    status_report = await _growth_service(db).build_autopilot_status(
        db,
        project_id,
        mode=mode,
        horizon_days=horizon_days,
        timezone=timezone,
        workflow_name=workflow_name,
    )
    return GrowthAutopilotStatusResponse(**status_report.to_dict())


@router.get("/oauth-audit", response_model=GrowthOAuthAuditResponse)
async def get_growth_oauth_audit(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GrowthOAuthAuditResponse:
    await get_accessible_project(db, project_id, user.id)
    audits = await _growth_service(db).audit_project_oauth(db, project_id)
    summary = summarize_oauth_audit(audits)
    return GrowthOAuthAuditResponse(**summary)


class GrowthChannelProfileResponse(BaseModel):
    channel_id: str
    project_id: str
    platform: str
    name: str
    score: float
    profile: dict = Field(default_factory=dict)
    report: dict = Field(default_factory=dict)
    analyzed_at: str | None = None
    is_active: bool = True
    has_credentials: bool = False


class ChannelIntelligenceResponse(BaseModel):
    channel_id: str
    project_id: str
    platform: str
    name: str
    confidence: str
    score: int
    summary: str
    niche: str = ""
    audience: str = ""
    brand_identity: dict = Field(default_factory=dict)
    visual_identity: dict = Field(default_factory=dict)
    content_patterns: dict = Field(default_factory=dict)
    historical_videos: dict = Field(default_factory=dict)
    posting_intelligence: dict = Field(default_factory=dict)
    competitor_intelligence: dict = Field(default_factory=dict)
    strategy_context: dict = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    generated_at: str = ""


class ChannelTwinResponse(BaseModel):
    channel_id: str
    project_id: str
    platform: str
    name: str
    status: str
    confidence: str
    score: int
    summary: str
    identity: dict = Field(default_factory=dict)
    brand_dna: dict = Field(default_factory=dict)
    audience: dict = Field(default_factory=dict)
    strategy: dict = Field(default_factory=dict)
    objectives: dict = Field(default_factory=dict)
    calendar: dict = Field(default_factory=dict)
    performance: dict = Field(default_factory=dict)
    competitors: dict = Field(default_factory=dict)
    community: dict = Field(default_factory=dict)
    learning: dict = Field(default_factory=dict)
    resources: dict = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    generated_at: str = ""


class VisualPatternResponse(BaseModel):
    project_id: str
    channel_id: str | None = None
    confidence: str
    score: int
    summary: str
    sample_size: int = 0
    pacing: str = "medium"
    movements: list[str] = Field(default_factory=list)
    transitions: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    scenarios: list[str] = Field(default_factory=list)
    framings: list[str] = Field(default_factory=list)
    emotions: list[str] = Field(default_factory=list)
    typography: dict = Field(default_factory=dict)
    subtitle_style: dict = Field(default_factory=dict)
    editor_hints: dict = Field(default_factory=dict)
    creative_hints: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    generated_at: str = ""


class GrowthCompetitorCreate(BaseModel):
    project_id: UUID
    platform: str
    handle: str
    display_name: str | None = None
    url: str | None = None
    notes: str = ""


class GrowthCompetitorResponse(BaseModel):
    id: str | None
    project_id: str
    platform: str
    handle: str
    display_name: str
    url: str | None = None
    notes: str = ""
    metrics: dict = Field(default_factory=dict)
    created_at: str | None = None
    last_synced_at: str | None = None
    last_analyzed_at: str | None = None
    analysis_score: float | None = None
    analysis_summary: str | None = None


class CompetitorSyncResponse(BaseModel):
    competitor_id: str
    synced: bool
    error: str | None = None
    metrics: dict = Field(default_factory=dict)


class CompetitorAnalysisResponse(BaseModel):
    competitor_id: str
    project_id: str
    platform: str
    handle: str
    display_name: str
    score: float
    summary: str
    patterns: dict = Field(default_factory=dict)
    recommendations: list[dict] = Field(default_factory=list)
    analyzed_at: str


def _competitor_response(row) -> GrowthCompetitorResponse:
    data = row.to_dict()
    metrics = data.get("metrics") or {}
    analysis = metrics.get("analysis") or {}
    return GrowthCompetitorResponse(
        **data,
        last_synced_at=metrics.get("last_synced_at"),
        last_analyzed_at=metrics.get("last_analyzed_at"),
        analysis_score=analysis.get("score"),
        analysis_summary=analysis.get("summary"),
    )


class GrowthRecommendationResponse(BaseModel):
    id: str | None
    project_id: str
    channel_id: str | None = None
    kind: str
    title: str
    detail: str
    priority: str
    source: str
    status: str
    created_at: str | None = None


class MarketSignalResponse(BaseModel):
    source: str
    title: str
    detail: str = ""
    score: float
    metadata: dict = Field(default_factory=dict)


class SaturationSignalResponse(BaseModel):
    topic: str
    level: str
    score: float
    reasons: list[str] = Field(default_factory=list)


class TrendOpportunityResponse(BaseModel):
    topic: str
    title: str
    score: float
    priority: str
    recommendation: str
    signals: list[MarketSignalResponse] = Field(default_factory=list)
    saturation: SaturationSignalResponse | None = None
    trend_brief: dict = Field(default_factory=dict)
    objective_id: str | None = None


class MarketIntelligenceResponse(BaseModel):
    project_id: str
    status: str
    summary: str
    opportunities: list[TrendOpportunityResponse] = Field(default_factory=list)
    saturation: list[SaturationSignalResponse] = Field(default_factory=list)
    signals: list[MarketSignalResponse] = Field(default_factory=list)
    generated_at: str = ""


class MarketRecommendationSyncResponse(BaseModel):
    report: MarketIntelligenceResponse
    recommendations_saved: int = 0


class GrowthStrategyResponse(BaseModel):
    project_id: str
    channel_id: str | None = None
    positioning: str = ""
    goals: list[str] = Field(default_factory=list)
    kpis: dict = Field(default_factory=dict)
    cadence: dict = Field(default_factory=dict)
    calendar: dict | None = None
    id: str | None = None
    updated_at: str | None = None


class GrowthReportResponse(BaseModel):
    project_id: str
    summary: str
    score: float
    generated_at: str = ""
    channels: list[GrowthChannelProfileResponse] = Field(default_factory=list)
    competitors: list[GrowthCompetitorResponse] = Field(default_factory=list)
    recommendations: list[GrowthRecommendationResponse] = Field(default_factory=list)
    strategy: GrowthStrategyResponse | None = None
    channel_health: list[dict] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    asset_ranking: list[dict] = Field(default_factory=list)
    report_detail: dict = Field(default_factory=dict)


class ContentCalendarItemResponse(BaseModel):
    id: str | None = None
    project_id: str
    channel_id: str | None = None
    title: str
    topic: str = ""
    planned_for: str | None = None
    status: str = "planned"
    metadata: dict = Field(default_factory=dict)
    created_at: str | None = None


class ContentStrategyPlanResponse(BaseModel):
    project_id: str
    strategy: GrowthStrategyResponse
    calendar: dict = Field(default_factory=dict)
    campaigns: list[dict] = Field(default_factory=list)
    channel_goals: dict = Field(default_factory=dict)
    summary: str = ""
    generated_at: str = ""


class AutonomousCalendarPlanResponse(BaseModel):
    project_id: str
    horizon_days: int
    mode: str
    status: str
    summary: str
    existing_items: int = 0
    proposed_items: list[dict] = Field(default_factory=list)
    calendar_items: list[dict] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    generated_at: str = ""


class AutonomousCalendarApplyResponse(BaseModel):
    plan: AutonomousCalendarPlanResponse
    saved_items: list[ContentCalendarItemResponse] = Field(default_factory=list)
    saved_count: int = 0


class CalendarProduceResponse(BaseModel):
    calendar_item_id: str
    pipeline_id: str
    status: str
    topic: str
    context_json: dict = Field(default_factory=dict)


class CalendarBatchProduceResponse(BaseModel):
    produced: list[CalendarProduceResponse] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)


class GrowthPlatformProfileResponse(BaseModel):
    id: str
    label: str
    oauth_supported: bool
    analytics_supported: bool
    publish_supported: bool
    content_variant_id: str | None = None
    content_types: list[str] = Field(default_factory=list)
    follower_field: str = ""
    primary_metric: str = ""
    max_duration_seconds: int | None = None
    weekly_posts_default: int = 3


class PostArtifactResponse(BaseModel):
    format: str
    title: str
    content: str
    data: dict = Field(default_factory=dict)
    source: str = "heuristic"


class CalendarPostGenerateResponse(BaseModel):
    calendar_item_id: str
    project_id: str
    topic: str
    platform: str
    content_type: str
    formats: list[str] = Field(default_factory=list)
    artifacts: list[PostArtifactResponse] = Field(default_factory=list)
    status: str = "post_ready"


class GrowthPostItemResponse(BaseModel):
    id: str | None = None
    project_id: str
    channel_id: str | None = None
    title: str
    topic: str = ""
    planned_for: str | None = None
    status: str = "planned"
    metadata: dict = Field(default_factory=dict)


class GrowthScheduleResponse(BaseModel):
    id: str
    project_id: str
    name: str
    topic: str
    cron_expression: str
    timezone: str
    is_active: bool
    next_run_at: str | None = None
    mode: str = "assisted"
    calendar_item_id: str
    calendar_status: str = "scheduled"
    planned_for: str | None = None


class GrowthScheduleCreateResponse(BaseModel):
    schedule: GrowthScheduleResponse
    calendar_item: ContentCalendarItemResponse


class GrowthScheduleSyncResponse(BaseModel):
    created: list[GrowthScheduleResponse] = Field(default_factory=list)
    count: int = 0


class CalendarDispatchResponse(BaseModel):
    mode: str
    calendar_item_id: str
    post: CalendarPostGenerateResponse | None = None
    produce: CalendarProduceResponse | None = None


def _growth_service(db: AsyncSession) -> GrowthService:
    return GrowthService(SqlAlchemyGrowthRepository(db))


async def _dispatch_growth_pipeline(
    db: AsyncSession,
    *,
    project_id: UUID,
    dispatch,
    user_id: UUID,
) -> UUID:
    project = await get_accessible_project(db, project_id, user_id)
    if project.org_id and quotas_enforced():
        try:
            await assert_can_start_pipeline(db, project.org_id)
        except QuotaExceededError as exc:
            raise HTTPException(
                status_code=429,
                detail={"error": "quota_exceeded", "kind": exc.kind, "limit": exc.limit, "current": exc.current},
            ) from exc
    if billing_enforced() and project.org_id:
        await ensure_org_billing(db, project.org_id)
        billing = await get_org_billing(db, project.org_id)
        cost = pipeline_credit_cost()
        if billing.credits_balance < cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits: have {billing.credits_balance}, need {cost}",
            )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.workflow_engine_url}/internal/pipelines",
                json=dispatch.to_workflow_request(auto_start=True),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Workflow engine unreachable: {exc}") from exc
    if resp.status_code != 201:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    pipeline_id = UUID(resp.json()["id"])
    pipeline = None
    for attempt in range(5):
        result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
        pipeline = result.scalar_one_or_none()
        if pipeline:
            break
        await asyncio.sleep(0.3 * (attempt + 1))
    if project.org_id and pipeline:
        try:
            await consume_pipeline_credit(db, project.org_id, pipeline_id)
        except InsufficientCreditsError as exc:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits: have {exc.balance}, need {exc.required}",
            ) from exc
    return pipeline_id


@router.get("/platforms", response_model=list[GrowthPlatformProfileResponse])
async def list_growth_platform_profiles(
    oauth_only: bool = Query(default=False),
    user: User = Depends(get_current_user),
) -> list[GrowthPlatformProfileResponse]:
    _ = user
    return [GrowthPlatformProfileResponse(**profile.to_dict()) for profile in list_growth_platforms(oauth_only=oauth_only)]


@router.get("/channels", response_model=list[GrowthChannelProfileResponse])
async def list_growth_channels(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[GrowthChannelProfileResponse]:
    await get_accessible_project(db, project_id, user.id)
    rows = await _growth_service(db).list_channels(project_id)
    return [GrowthChannelProfileResponse(**row.to_dict()) for row in rows]


class ChannelScopeResponse(BaseModel):
    org_id: str | None = None
    project_id: str
    channel_id: str
    platform: str
    channel_name: str


class ChannelOverviewItemResponse(BaseModel):
    channel_id: str
    project_id: str
    platform: str
    name: str
    score: float
    health_status: str
    calendar_planned: int
    calendar_scheduled: int
    recommendations_open: int
    has_credentials: bool
    is_active: bool


class ChannelWorkspaceResponse(BaseModel):
    scope: ChannelScopeResponse
    profile: GrowthChannelProfileResponse | None = None
    memory: dict = Field(default_factory=dict)
    analytics: dict = Field(default_factory=dict)
    performance: list[dict] = Field(default_factory=list)
    learning: list[dict] = Field(default_factory=list)
    calendar: list[ContentCalendarItemResponse] = Field(default_factory=list)
    strategy: GrowthStrategyResponse | None = None
    recommendations: list[GrowthRecommendationResponse] = Field(default_factory=list)
    competitors: list[GrowthCompetitorResponse] = Field(default_factory=list)
    assets: list[dict] = Field(default_factory=list)
    manager_plan: dict | None = None
    summary: str = ""
    health_status: str = "unknown"


@router.get("/channels/overview", response_model=list[ChannelOverviewItemResponse])
async def list_growth_channels_overview(
    project_id: UUID,
    horizon_days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ChannelOverviewItemResponse]:
    await get_accessible_project(db, project_id, user.id)
    items = await _growth_service(db).list_project_channels_overview(db, project_id, horizon_days=horizon_days)
    return [ChannelOverviewItemResponse(**item.to_dict()) for item in items]


@router.get("/channels/{channel_id}/workspace", response_model=ChannelWorkspaceResponse)
async def get_channel_workspace(
    channel_id: UUID,
    horizon_days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChannelWorkspaceResponse:
    channel = await db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    project = await get_accessible_project(db, channel.project_id, user.id)
    try:
        workspace = await _growth_service(db).get_channel_workspace(
            db,
            channel_id,
            org_id=project.org_id,
            horizon_days=horizon_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    data = workspace.to_dict()
    return ChannelWorkspaceResponse(
        scope=ChannelScopeResponse(**data["scope"]),
        profile=GrowthChannelProfileResponse(**data["profile"]) if data.get("profile") else None,
        memory=data.get("memory") or {},
        analytics=data.get("analytics") or {},
        performance=data.get("performance") or [],
        learning=data.get("learning") or [],
        calendar=[ContentCalendarItemResponse(**item) for item in data.get("calendar") or []],
        strategy=GrowthStrategyResponse(**data["strategy"]) if data.get("strategy") else None,
        recommendations=[GrowthRecommendationResponse(**rec) for rec in data.get("recommendations") or []],
        competitors=[_competitor_response_from_dict(comp) for comp in data.get("competitors") or []],
        assets=data.get("assets") or [],
        manager_plan=data.get("manager_plan"),
        summary=data.get("summary") or "",
        health_status=data.get("health_status") or "unknown",
    )


@router.get("/channels/{channel_id}/intelligence", response_model=ChannelIntelligenceResponse)
async def get_channel_intelligence(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChannelIntelligenceResponse:
    channel = await db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    await get_accessible_project(db, channel.project_id, user.id)
    try:
        snapshot = await _growth_service(db).build_channel_intelligence_snapshot(db, channel_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ChannelIntelligenceResponse(**snapshot.to_dict())


@router.get("/channels/{channel_id}/twin", response_model=ChannelTwinResponse)
async def get_channel_twin(
    channel_id: UUID,
    horizon_days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChannelTwinResponse:
    channel = await db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    await get_accessible_project(db, channel.project_id, user.id)
    try:
        provider = GrowthChannelTwinProvider(_growth_service(db), db)
        twin = await provider.build_channel_twin(str(channel_id), horizon_days=horizon_days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ChannelTwinResponse(**twin.to_dict())


@router.get("/channels/{channel_id}/visual-intelligence", response_model=VisualPatternResponse)
async def get_channel_visual_intelligence(
    channel_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> VisualPatternResponse:
    channel = await db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    await get_accessible_project(db, channel.project_id, user.id)

    workspace = await _growth_service(db).get_channel_workspace(db, channel_id, horizon_days=30)
    asset_ids = [
        item.get("asset_id")
        for item in workspace.to_dict().get("assets") or []
        if item.get("asset_id")
    ]
    query = select(AssetMediaProfile).where(AssetMediaProfile.project_id == channel.project_id)
    if asset_ids:
        query = query.where(AssetMediaProfile.asset_id.in_([UUID(str(asset_id)) for asset_id in asset_ids]))
    result = await db.execute(query.order_by(AssetMediaProfile.updated_at.desc()).limit(limit))
    profiles = [
        {
            "asset_id": str(row.asset_id),
            "analysis": row.analysis or {},
            "vision_model": row.vision_model,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in result.scalars().all()
    ]
    snapshot = build_visual_pattern_snapshot(
        project_id=str(channel.project_id),
        channel_id=str(channel_id),
        media_profiles=profiles,
    )
    return VisualPatternResponse(**snapshot.to_dict())


def _competitor_response_from_dict(data: dict) -> GrowthCompetitorResponse:
    metrics = data.get("metrics") or {}
    analysis = metrics.get("analysis") or {}
    return GrowthCompetitorResponse(
        **data,
        last_synced_at=metrics.get("last_synced_at"),
        last_analyzed_at=metrics.get("last_analyzed_at"),
        analysis_score=analysis.get("score"),
        analysis_summary=analysis.get("summary"),
    )


@router.get("/competitors", response_model=list[GrowthCompetitorResponse])
async def list_growth_competitors(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[GrowthCompetitorResponse]:
    await get_accessible_project(db, project_id, user.id)
    rows = await _growth_service(db).list_competitors(project_id)
    return [_competitor_response(row) for row in rows]


@router.post("/competitors", response_model=GrowthCompetitorResponse, status_code=status.HTTP_201_CREATED)
async def create_growth_competitor(
    body: GrowthCompetitorCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> GrowthCompetitorResponse:
    await get_accessible_project(db, body.project_id, user.id)
    competitor = await _growth_service(db).create_competitor(
        body.project_id,
        platform=body.platform,
        handle=body.handle,
        display_name=body.display_name or body.handle,
        url=body.url,
        notes=body.notes,
    )
    await db.commit()
    return _competitor_response(competitor)


@router.get("/competitors/{competitor_id}", response_model=GrowthCompetitorResponse)
async def get_growth_competitor(
    competitor_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GrowthCompetitorResponse:
    service = _growth_service(db)
    competitor = await service.get_competitor(competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    await get_accessible_project(db, UUID(competitor.project_id), user.id)
    return _competitor_response(competitor)


@router.post("/competitors/{competitor_id}/sync", response_model=CompetitorSyncResponse)
async def sync_growth_competitor(
    competitor_id: UUID,
    limit: int = Query(default=10, ge=1, le=25),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> CompetitorSyncResponse:
    service = _growth_service(db)
    competitor = await service.get_competitor(competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    await get_accessible_project(db, UUID(competitor.project_id), user.id)
    try:
        updated = await service.sync_competitor(competitor_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    metrics = updated.metrics or {}
    return CompetitorSyncResponse(
        competitor_id=str(competitor_id),
        synced=not metrics.get("sync_error"),
        error=metrics.get("sync_error"),
        metrics=metrics,
    )


@router.post("/competitors/{competitor_id}/analyze", response_model=CompetitorAnalysisResponse)
async def analyze_growth_competitor(
    competitor_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> CompetitorAnalysisResponse:
    service = _growth_service(db)
    competitor = await service.get_competitor(competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    await get_accessible_project(db, UUID(competitor.project_id), user.id)
    try:
        analysis = await service.analyze_competitor(competitor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return CompetitorAnalysisResponse(**analysis.to_dict())


@router.post("/competitors/sync-all", response_model=list[CompetitorSyncResponse])
async def sync_all_growth_competitors(
    project_id: UUID,
    limit: int = Query(default=10, ge=1, le=25),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> list[CompetitorSyncResponse]:
    await get_accessible_project(db, project_id, user.id)
    service = _growth_service(db)
    results = await service.sync_project_competitors(project_id, limit=limit)
    await db.commit()
    return [
        CompetitorSyncResponse(
            competitor_id=item["competitor_id"],
            synced=item["synced"],
            error=item.get("error"),
        )
        for item in results
    ]


@router.get("/report", response_model=GrowthReportResponse)
async def get_growth_report(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GrowthReportResponse:
    await get_accessible_project(db, project_id, user.id)
    report = await _growth_service(db).build_report(db, project_id)
    await db.commit()
    return GrowthReportResponse(**report.to_dict())


@router.get("/strategy", response_model=GrowthStrategyResponse)
async def get_growth_strategy(
    project_id: UUID,
    channel_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GrowthStrategyResponse:
    await get_accessible_project(db, project_id, user.id)
    if channel_id is not None:
        channel = await db.get(Channel, channel_id)
        if not channel or channel.project_id != project_id:
            raise HTTPException(status_code=404, detail="Channel not found in project")
    strategy = await _growth_service(db).get_strategy(project_id, channel_id=channel_id)
    return GrowthStrategyResponse(**strategy.to_dict())


@router.post("/strategy/generate", response_model=ContentStrategyPlanResponse)
async def generate_growth_strategy(
    project_id: UUID,
    horizon_days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> ContentStrategyPlanResponse:
    await _enforce_growth_rate_limit(user, "strategy_generate")
    await get_accessible_project(db, project_id, user.id)
    plan = await _growth_service(db).generate_content_strategy(db, project_id, horizon_days=horizon_days)
    await db.commit()
    return ContentStrategyPlanResponse(**plan.to_dict())


@router.get("/calendar", response_model=list[ContentCalendarItemResponse])
async def get_growth_calendar(
    project_id: UUID,
    horizon_days: int = Query(default=30, ge=7, le=90),
    channel_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ContentCalendarItemResponse]:
    await get_accessible_project(db, project_id, user.id)
    if channel_id is not None:
        channel = await db.get(Channel, channel_id)
        if not channel or channel.project_id != project_id:
            raise HTTPException(status_code=404, detail="Channel not found in project")
    items = await _growth_service(db).get_content_calendar(
        project_id,
        horizon_days=horizon_days,
        channel_id=channel_id,
    )
    return [ContentCalendarItemResponse(**item) for item in items]


@router.get("/calendar/autonomous-plan", response_model=AutonomousCalendarPlanResponse)
async def preview_autonomous_growth_calendar(
    project_id: UUID,
    channel_id: UUID | None = Query(default=None),
    horizon_days: int = Query(default=30, ge=7, le=90),
    max_items: int = Query(default=20, ge=1, le=50),
    mode: str = Query(default="draft", pattern="^(draft|manual|assisted|automatic|auto|assistido)$"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AutonomousCalendarPlanResponse:
    await get_accessible_project(db, project_id, user.id)
    if channel_id is not None:
        channel = await db.get(Channel, channel_id)
        if not channel or channel.project_id != project_id:
            raise HTTPException(status_code=404, detail="Channel not found in project")
    try:
        plan = await _growth_service(db).build_autonomous_calendar_plan(
            db,
            project_id,
            channel_id=channel_id,
            horizon_days=horizon_days,
            max_items=max_items,
            mode=mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AutonomousCalendarPlanResponse(**plan.to_dict())


@router.post("/calendar/autonomous-plan/apply", response_model=AutonomousCalendarApplyResponse)
async def apply_autonomous_growth_calendar(
    project_id: UUID,
    channel_id: UUID | None = Query(default=None),
    horizon_days: int = Query(default=30, ge=7, le=90),
    max_items: int = Query(default=20, ge=1, le=50),
    mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> AutonomousCalendarApplyResponse:
    await _enforce_growth_rate_limit(user, "autonomous_calendar")
    await get_accessible_project(db, project_id, user.id)
    if channel_id is not None:
        channel = await db.get(Channel, channel_id)
        if not channel or channel.project_id != project_id:
            raise HTTPException(status_code=404, detail="Channel not found in project")
    try:
        plan, saved = await _growth_service(db).apply_autonomous_calendar_plan(
            db,
            project_id,
            channel_id=channel_id,
            horizon_days=horizon_days,
            max_items=max_items,
            mode=mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return AutonomousCalendarApplyResponse(
        plan=AutonomousCalendarPlanResponse(**plan.to_dict()),
        saved_items=[ContentCalendarItemResponse(**item) for item in saved],
        saved_count=len(saved),
    )


@router.post("/calendar/{calendar_item_id}/produce", response_model=CalendarProduceResponse)
async def produce_growth_calendar_item(
    calendar_item_id: UUID,
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> CalendarProduceResponse:
    await _enforce_growth_rate_limit(user, "produce")
    service = _growth_service(db)
    try:
        dispatch = await service.prepare_calendar_dispatch(calendar_item_id, workflow_name=workflow_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    project_id = UUID(dispatch.project_id)
    await get_accessible_project(db, project_id, user.id)
    pipeline_id = await _dispatch_growth_pipeline(db, project_id=project_id, dispatch=dispatch, user_id=user.id)
    updated = await service.mark_calendar_dispatched(calendar_item_id, pipeline_id=pipeline_id)
    await db.commit()
    return CalendarProduceResponse(
        calendar_item_id=str(calendar_item_id),
        pipeline_id=str(pipeline_id),
        status=updated.get("status", "dispatched"),
        topic=dispatch.topic,
        context_json=dispatch.context_json,
    )


@router.post("/calendar/produce-planned", response_model=CalendarBatchProduceResponse)
async def produce_planned_growth_calendar(
    project_id: UUID,
    limit: int = Query(default=3, ge=1, le=10),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> CalendarBatchProduceResponse:
    await get_accessible_project(db, project_id, user.id)
    service = _growth_service(db)
    planned = await service.list_planned_calendar_items(project_id, limit=limit)
    produced: list[CalendarProduceResponse] = []
    errors: list[dict] = []

    for item in planned:
        item_id = item.get("id")
        if not item_id:
            continue
        try:
            dispatch = await service.prepare_calendar_dispatch(UUID(item_id), workflow_name=workflow_name)
            pipeline_id = await _dispatch_growth_pipeline(
                db, project_id=project_id, dispatch=dispatch, user_id=user.id
            )
            updated = await service.mark_calendar_dispatched(UUID(item_id), pipeline_id=pipeline_id)
            produced.append(
                CalendarProduceResponse(
                    calendar_item_id=str(item_id),
                    pipeline_id=str(pipeline_id),
                    status=updated.get("status", "dispatched"),
                    topic=dispatch.topic,
                    context_json=dispatch.context_json,
                )
            )
        except HTTPException as exc:
            errors.append({"calendar_item_id": item_id, "detail": exc.detail})
            break
        except ValueError as exc:
            errors.append({"calendar_item_id": item_id, "detail": str(exc)})
        except Exception as exc:
            errors.append({"calendar_item_id": item_id, "detail": str(exc)})

    await db.commit()
    return CalendarBatchProduceResponse(produced=produced, errors=errors)


def _post_generate_response(result, *, status: str = "post_ready") -> CalendarPostGenerateResponse:
    return CalendarPostGenerateResponse(
        calendar_item_id=result.calendar_item_id,
        project_id=result.project_id,
        topic=result.topic,
        platform=result.platform,
        content_type=result.content_type,
        formats=result.formats,
        artifacts=[
            PostArtifactResponse(
                format=a.get("format", ""),
                title=a.get("title", ""),
                content=a.get("content", ""),
                data=a.get("data") or {},
                source=a.get("source", "heuristic"),
            )
            for a in result.artifacts
        ],
        status=status,
    )


@router.post("/calendar/{calendar_item_id}/generate-post", response_model=CalendarPostGenerateResponse)
async def generate_growth_calendar_post(
    calendar_item_id: UUID,
    include_companion: bool = Query(default=False),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> CalendarPostGenerateResponse:
    service = _growth_service(db)
    item = await service.get_calendar_item(calendar_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Calendar item not found")
    await get_accessible_project(db, UUID(item["project_id"]), user.id)
    try:
        result = await service.generate_calendar_post(calendar_item_id, include_companion=include_companion)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return _post_generate_response(result)


@router.post("/calendar/{calendar_item_id}/dispatch", response_model=CalendarDispatchResponse)
async def dispatch_growth_calendar_item(
    calendar_item_id: UUID,
    workflow_name: str | None = Query(default=None),
    include_companion: bool = Query(default=False),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> CalendarDispatchResponse:
    service = _growth_service(db)
    item = await service.get_calendar_item(calendar_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Calendar item not found")
    project_id = UUID(item["project_id"])
    await get_accessible_project(db, project_id, user.id)

    metadata = item.get("metadata") or {}
    content_type = str(metadata.get("content_type") or "video").lower()

    post_response = None
    if include_companion and not is_text_content_type(content_type):
        try:
            companion = await service.generate_calendar_post(calendar_item_id, include_companion=True, companion=True)
            post_response = _post_generate_response(companion, status=item.get("status", "planned"))
        except ValueError:
            pass

    if is_text_content_type(content_type):
        try:
            result = await service.generate_calendar_post(calendar_item_id, include_companion=include_companion)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        await db.commit()
        return CalendarDispatchResponse(
            mode="text",
            calendar_item_id=str(calendar_item_id),
            post=_post_generate_response(result),
        )

    try:
        dispatch = await service.prepare_calendar_dispatch(calendar_item_id, workflow_name=workflow_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    pipeline_id = await _dispatch_growth_pipeline(db, project_id=project_id, dispatch=dispatch, user_id=user.id)
    updated = await service.mark_calendar_dispatched(calendar_item_id, pipeline_id=pipeline_id)
    await db.commit()
    return CalendarDispatchResponse(
        mode="video",
        calendar_item_id=str(calendar_item_id),
        produce=CalendarProduceResponse(
            calendar_item_id=str(calendar_item_id),
            pipeline_id=str(pipeline_id),
            status=updated.get("status", "dispatched"),
            topic=dispatch.topic,
            context_json=dispatch.context_json,
        ),
        post=post_response,
    )


@router.get("/posts", response_model=list[GrowthPostItemResponse])
async def list_growth_posts(
    project_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[GrowthPostItemResponse]:
    await get_accessible_project(db, project_id, user.id)
    items = await _growth_service(db).list_calendar_posts(project_id, limit=limit)
    return [GrowthPostItemResponse(**item) for item in items]


def _schedule_response(result: dict, plan_mode: str | None = None) -> GrowthScheduleResponse:
    calendar = result.get("calendar_item") or {}
    metadata = calendar.get("metadata") or {}
    return GrowthScheduleResponse(
        id=str(result["id"]),
        project_id=str(result["project_id"]),
        name=result["name"],
        topic=result["topic"],
        cron_expression=result["cron_expression"],
        timezone=result["timezone"],
        is_active=bool(result["is_active"]),
        next_run_at=result.get("next_run_at"),
        mode=str(plan_mode or metadata.get("scheduling_mode") or "assisted"),
        calendar_item_id=str(calendar.get("id") or metadata.get("growth_plan_id") or ""),
        calendar_status=str(calendar.get("status") or "scheduled"),
        planned_for=calendar.get("planned_for"),
    )


@router.post("/calendar/{calendar_item_id}/schedule", response_model=GrowthScheduleCreateResponse)
async def schedule_growth_calendar_item(
    calendar_item_id: UUID,
    mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    timezone: str = Query(default="UTC"),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> GrowthScheduleCreateResponse:
    service = _growth_service(db)
    item = await service.get_calendar_item(calendar_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Calendar item not found")
    project = await get_accessible_project(db, UUID(item["project_id"]), user.id)
    try:
        plan, result = await service.schedule_calendar_item(
            db,
            calendar_item_id,
            user_id=user.id,
            org_id=project.org_id,
            mode=mode,
            timezone=timezone,
            workflow_name=workflow_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    calendar_item = result.pop("calendar_item", {})
    return GrowthScheduleCreateResponse(
        schedule=_schedule_response(result, plan.mode),
        calendar_item=ContentCalendarItemResponse(**calendar_item),
    )


@router.post("/calendar/{calendar_item_id}/schedule/approve", response_model=ContentCalendarItemResponse)
async def approve_growth_calendar_schedule(
    calendar_item_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> ContentCalendarItemResponse:
    service = _growth_service(db)
    item = await service.get_calendar_item(calendar_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Calendar item not found")
    await get_accessible_project(db, UUID(item["project_id"]), user.id)
    try:
        updated = await service.approve_calendar_schedule(db, calendar_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return ContentCalendarItemResponse(**updated)


@router.post("/calendar/sync-schedules", response_model=GrowthScheduleSyncResponse)
async def sync_growth_calendar_schedules(
    project_id: UUID,
    mode: str = Query(default="assisted"),
    timezone: str = Query(default="UTC"),
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> GrowthScheduleSyncResponse:
    project = await get_accessible_project(db, project_id, user.id)
    service = _growth_service(db)
    created = await service.sync_calendar_schedules(
        db,
        project_id,
        user_id=user.id,
        org_id=project.org_id,
        mode=mode,
        timezone=timezone,
        limit=limit,
    )
    await db.commit()
    return GrowthScheduleSyncResponse(
        created=[_schedule_response(row) for row in created],
        count=len(created),
    )


@router.get("/schedules", response_model=list[GrowthScheduleResponse])
async def list_growth_schedules(
    project_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[GrowthScheduleResponse]:
    await get_accessible_project(db, project_id, user.id)
    items = await _growth_service(db).list_scheduled_calendar_items(project_id, limit=limit)
    responses: list[GrowthScheduleResponse] = []
    for item in items:
        metadata = item.get("metadata") or {}
        schedule_id = metadata.get("schedule_id")
        if not schedule_id:
            continue
        responses.append(
            GrowthScheduleResponse(
                id=str(schedule_id),
                project_id=str(item["project_id"]),
                name=f"Growth: {item.get('title', '')}"[:120],
                topic=str(item.get("topic") or item.get("title") or ""),
                cron_expression=str(metadata.get("cron_expression") or ""),
                timezone="UTC",
                is_active=item.get("status") == "scheduled",
                next_run_at=item.get("planned_for"),
                mode=str(metadata.get("scheduling_mode") or "assisted"),
                calendar_item_id=str(item.get("id") or ""),
                calendar_status=str(item.get("status") or ""),
                planned_for=item.get("planned_for"),
            )
        )
    return responses


class GrowthPerformanceResponse(BaseModel):
    project_id: str
    summary: str = ""
    total_media: int = 0
    high_performers: int = 0
    low_performers: int = 0
    avg_ctr: float | None = None
    avg_retention: float | None = None
    platform_breakdown: list[dict] = Field(default_factory=list)
    top_hooks: list[str] = Field(default_factory=list)
    top_assets: list[dict] = Field(default_factory=list)
    underperformers: list[dict] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[GrowthRecommendationResponse] = Field(default_factory=list)


class GrowthPerformanceSyncResponse(BaseModel):
    interpretation: GrowthPerformanceResponse
    recommendations_saved: int = 0


class ChannelManagerActionResponse(BaseModel):
    action: str
    title: str
    detail: str
    priority: str = "medium"
    calendar_item_id: str | None = None
    can_execute: bool = False
    block_reason: str | None = None
    execution: dict = Field(default_factory=dict)


class ChannelManagerPlanResponse(BaseModel):
    channel_id: str
    project_id: str
    platform: str
    channel_name: str
    summary: str
    health_status: str
    focus_topics: list[str] = Field(default_factory=list)
    actions: list[ChannelManagerActionResponse] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    signals_summary: dict = Field(default_factory=dict)
    generated_at: str = ""


class ChannelManagerRunResult(BaseModel):
    action: str
    status: str
    detail: str
    calendar_item_id: str | None = None
    pipeline_id: str | None = None
    schedule_id: str | None = None


class ChannelManagerExecuteResponse(BaseModel):
    plan: ChannelManagerPlanResponse
    executed: list[ChannelManagerRunResult] = Field(default_factory=list)
    dry_run: bool = True


class GrowthAutonomousRunResponse(BaseModel):
    plan: GrowthAutonomousExecutionPlanResponse
    executed: list[ChannelManagerRunResult] = Field(default_factory=list)
    dry_run: bool = True


def _channel_manager_plan_response(plan) -> ChannelManagerPlanResponse:
    data = plan.to_dict()
    return ChannelManagerPlanResponse(
        **{k: v for k, v in data.items() if k != "actions"},
        actions=[ChannelManagerActionResponse(**action) for action in data.get("actions") or []],
    )


async def _execute_channel_manager_action(
    db: AsyncSession,
    *,
    service: GrowthService,
    user: User,
    channel: Channel,
    action: dict,
    scheduling_mode: str,
    timezone: str,
    workflow_name: str | None,
) -> ChannelManagerRunResult:
    kind = action.get("action")
    calendar_item_id = action.get("calendar_item_id")
    if not action.get("can_execute"):
        return ChannelManagerRunResult(
            action=str(kind),
            status="skipped",
            detail=action.get("block_reason") or "Ação não executável",
            calendar_item_id=calendar_item_id,
        )

    project = await get_accessible_project(db, channel.project_id, user.id)

    if kind == "produce" and calendar_item_id:
        dispatch = await service.prepare_calendar_dispatch(UUID(calendar_item_id), workflow_name=workflow_name)
        pipeline_id = await _dispatch_growth_pipeline(
            db,
            project_id=channel.project_id,
            dispatch=dispatch,
            user_id=user.id,
        )
        await service.mark_calendar_dispatched(UUID(calendar_item_id), pipeline_id=pipeline_id)
        return ChannelManagerRunResult(
            action=kind,
            status="ok",
            detail=f"Pipeline {pipeline_id} criado via Workflow Engine",
            calendar_item_id=calendar_item_id,
            pipeline_id=str(pipeline_id),
        )

    if kind == "schedule" and calendar_item_id:
        _, result = await service.schedule_calendar_item(
            db,
            UUID(calendar_item_id),
            user_id=user.id,
            org_id=project.org_id,
            mode=scheduling_mode,
            timezone=timezone,
            workflow_name=workflow_name,
        )
        return ChannelManagerRunResult(
            action=kind,
            status="ok",
            detail="Agendamento criado no Smart Scheduler",
            calendar_item_id=calendar_item_id,
            schedule_id=str(result.get("id")),
        )

    if kind == "generate_post" and calendar_item_id:
        result = await service.generate_calendar_post(UUID(calendar_item_id))
        return ChannelManagerRunResult(
            action=kind,
            status="ok",
            detail=f"Post gerado ({', '.join(result.formats)})",
            calendar_item_id=calendar_item_id,
        )

    if kind == "analyze":
        from contentos_intelligence.application.platform_analytics.service import get_latest_channel_overview

        overview = await get_latest_channel_overview(db, channel.id, platform=channel.platform.lower())
        if not overview:
            return ChannelManagerRunResult(
                action=kind,
                status="error",
                detail="Sem dados sincronizados — execute sync OAuth primeiro",
            )
        analysis = await service.analyze_channel(
            db=db,
            channel_id=channel.id,
            project_id=channel.project_id,
            platform=channel.platform,
            channel_name=channel.name,
            overview=overview,
        )
        return ChannelManagerRunResult(
            action=kind,
            status="ok",
            detail=f"Análise concluída — score {analysis.score:.0f}",
        )

    return ChannelManagerRunResult(
        action=str(kind),
        status="skipped",
        detail="Ação informativa — sem execução automática",
        calendar_item_id=calendar_item_id,
    )


@router.get("/channels/{channel_id}/manager/plan", response_model=ChannelManagerPlanResponse)
async def get_channel_manager_plan(
    channel_id: UUID,
    scheduling_mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    timezone: str = Query(default="UTC"),
    horizon_days: int = Query(default=7, ge=1, le=30),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChannelManagerPlanResponse:
    channel = await db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    await get_accessible_project(db, channel.project_id, user.id)
    try:
        plan = await _growth_service(db).build_channel_manager_plan(
            db,
            channel_id,
            scheduling_mode=scheduling_mode,
            timezone=timezone,
            horizon_days=horizon_days,
            workflow_name=workflow_name,
            persist=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return _channel_manager_plan_response(plan)


@router.post("/channels/{channel_id}/manager/run", response_model=ChannelManagerExecuteResponse)
async def run_channel_manager(
    channel_id: UUID,
    dry_run: bool = Query(default=True),
    max_actions: int = Query(default=3, ge=1, le=10),
    scheduling_mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    timezone: str = Query(default="UTC"),
    horizon_days: int = Query(default=7, ge=1, le=30),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> ChannelManagerExecuteResponse:
    if not dry_run:
        await _enforce_growth_rate_limit(user, "channel_manager_run")
    channel = await db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    await get_accessible_project(db, channel.project_id, user.id)
    service = _growth_service(db)
    try:
        plan = await service.build_channel_manager_plan(
            db,
            channel_id,
            scheduling_mode=scheduling_mode,
            timezone=timezone,
            horizon_days=horizon_days,
            workflow_name=workflow_name,
            persist=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    plan_response = _channel_manager_plan_response(plan)
    if dry_run:
        await db.commit()
        return ChannelManagerExecuteResponse(plan=plan_response, executed=[], dry_run=True)

    executed: list[ChannelManagerRunResult] = []
    for action in plan_response.actions[:max_actions]:
        if action.action in ("recommend",):
            continue
        try:
            result = await _execute_channel_manager_action(
                db,
                service=service,
                user=user,
                channel=channel,
                action=action.model_dump(),
                scheduling_mode=scheduling_mode,
                timezone=timezone,
                workflow_name=workflow_name,
            )
            executed.append(result)
        except HTTPException:
            raise
        except ValueError as exc:
            executed.append(
                ChannelManagerRunResult(
                    action=action.action,
                    status="error",
                    detail=str(exc),
                    calendar_item_id=action.calendar_item_id,
                )
            )

    await db.commit()
    return ChannelManagerExecuteResponse(plan=plan_response, executed=executed, dry_run=False)


@router.get("/autopilot/execution-plan", response_model=GrowthAutonomousExecutionPlanResponse)
async def get_growth_autonomous_execution_plan(
    project_id: UUID,
    mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    horizon_days: int = Query(default=7, ge=1, le=30),
    max_actions: int = Query(default=5, ge=1, le=20),
    timezone: str = Query(default="UTC"),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GrowthAutonomousExecutionPlanResponse:
    await get_accessible_project(db, project_id, user.id)
    plan = await _growth_service(db).build_autonomous_execution_plan(
        db,
        project_id,
        mode=mode,
        horizon_days=horizon_days,
        max_actions=max_actions,
        timezone=timezone,
        workflow_name=workflow_name,
    )
    return GrowthAutonomousExecutionPlanResponse(**plan.to_dict())


@router.post("/autopilot/run", response_model=GrowthAutonomousRunResponse)
async def run_growth_autopilot(
    project_id: UUID,
    dry_run: bool = Query(default=True),
    mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    horizon_days: int = Query(default=7, ge=1, le=30),
    max_actions: int = Query(default=5, ge=1, le=20),
    timezone: str = Query(default="UTC"),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> GrowthAutonomousRunResponse:
    if not dry_run:
        await _enforce_growth_rate_limit(user, "autopilot_run")
    await get_accessible_project(db, project_id, user.id)
    service = _growth_service(db)
    plan = await service.build_autonomous_execution_plan(
        db,
        project_id,
        mode=mode,
        horizon_days=horizon_days,
        max_actions=max_actions,
        timezone=timezone,
        workflow_name=workflow_name,
    )
    plan_response = GrowthAutonomousExecutionPlanResponse(**plan.to_dict())
    if dry_run:
        return GrowthAutonomousRunResponse(plan=plan_response, executed=[], dry_run=True)

    executed: list[ChannelManagerRunResult] = []
    channels_by_id: dict[str, Channel] = {}
    rows = (
        await db.execute(select(Channel).where(Channel.project_id == project_id))
    ).scalars().all()
    for channel in rows:
        channels_by_id[str(channel.id)] = channel

    for action in plan_response.actions[:max_actions]:
        channel = channels_by_id.get(str(action.get("channel_id") or ""))
        if not channel:
            executed.append(
                ChannelManagerRunResult(
                    action=str(action.get("action") or ""),
                    status="error",
                    detail="Canal não encontrado para executar ação",
                    calendar_item_id=action.get("calendar_item_id"),
                )
            )
            continue
        try:
            result = await _execute_channel_manager_action(
                db,
                service=service,
                user=user,
                channel=channel,
                action=action,
                scheduling_mode=mode,
                timezone=timezone,
                workflow_name=workflow_name,
            )
            executed.append(result)
        except HTTPException:
            raise
        except ValueError as exc:
            executed.append(
                ChannelManagerRunResult(
                    action=str(action.get("action") or ""),
                    status="error",
                    detail=str(exc),
                    calendar_item_id=action.get("calendar_item_id"),
                )
            )

    await db.commit()
    return GrowthAutonomousRunResponse(plan=plan_response, executed=executed, dry_run=False)


@router.get("/autopilot/closed-loop", response_model=GrowthClosedLoopResponse)
async def get_growth_closed_loop(
    project_id: UUID,
    mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    horizon_days: int = Query(default=7, ge=1, le=30),
    max_actions: int = Query(default=5, ge=1, le=20),
    timezone: str = Query(default="UTC"),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GrowthClosedLoopResponse:
    await get_accessible_project(db, project_id, user.id)
    report = await _growth_service(db).build_closed_loop_report(
        db,
        project_id,
        sync_performance=False,
        mode=mode,
        horizon_days=horizon_days,
        max_actions=max_actions,
        timezone=timezone,
        workflow_name=workflow_name,
        persist_report=False,
    )
    return GrowthClosedLoopResponse(**report.to_dict())


@router.post("/autopilot/closed-loop/sync", response_model=GrowthClosedLoopResponse)
async def sync_growth_closed_loop(
    project_id: UUID,
    sync_performance: bool = Query(default=True),
    save_recommendations: bool = Query(default=True),
    mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    horizon_days: int = Query(default=7, ge=1, le=30),
    max_actions: int = Query(default=5, ge=1, le=20),
    timezone: str = Query(default="UTC"),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> GrowthClosedLoopResponse:
    await _enforce_growth_rate_limit(user, "closed_loop_sync")
    await get_accessible_project(db, project_id, user.id)
    report = await _growth_service(db).build_closed_loop_report(
        db,
        project_id,
        sync_performance=sync_performance,
        save_recommendations=save_recommendations,
        mode=mode,
        horizon_days=horizon_days,
        max_actions=max_actions,
        timezone=timezone,
        workflow_name=workflow_name,
        persist_report=True,
    )
    await db.commit()
    return GrowthClosedLoopResponse(**report.to_dict())



async def _build_temporal_closed_loop_policy(
    db: AsyncSession,
    project_id: UUID,
    *,
    published_at: str | None,
    sync_performance: bool,
    save_recommendations: bool,
    mode: str,
    horizon_days: int,
    max_actions: int,
    timezone: str,
    workflow_name: str | None,
    persist_report: bool,
) -> tuple[dict, int]:
    service = _growth_service(db)
    before_count = len(await service.list_recommendations(project_id))
    closed_loop = await service.build_closed_loop_report(
        db,
        project_id,
        sync_performance=sync_performance,
        save_recommendations=save_recommendations,
        mode=mode,
        horizon_days=horizon_days,
        max_actions=max_actions,
        timezone=timezone,
        workflow_name=workflow_name,
        persist_report=persist_report,
    )
    strategy = await service.get_strategy(project_id)
    objectives = {"nodes": []}
    if strategy and strategy.goals:
        objectives = {
            "nodes": [
                {"id": f"strategy-goal-{index}", "title": goal, "level": "project"}
                for index, goal in enumerate(strategy.goals, start=1)
            ]
        }
    policy = build_closed_loop_cycle_policy(
        project_id=str(project_id),
        published_at=published_at,
        closed_loop_report=closed_loop.to_dict(),
        objectives=objectives,
        recommendations_version=before_count + 1,
    )
    saved = 0
    if save_recommendations and persist_report and policy.versioned_recommendations:
        saved = await service.save_recommendations(
            project_id,
            [
                GrowthRecommendation(
                    id=None,
                    project_id=str(project_id),
                    channel_id=item.get("channel_id"),
                    kind=str(item.get("kind") or "closed_learning"),
                    title=str(item.get("title") or "Closed Learning Temporal"),
                    detail=str(item.get("detail") or ""),
                    priority=str(item.get("priority") or "medium"),
                    source=str(item.get("source") or "closed_learning_temporal"),
                    status=str(item.get("status") or "open"),
                    created_at=None,
                )
                for item in policy.versioned_recommendations
            ],
        )
    return policy.to_dict(), saved


@router.get("/autopilot/closed-loop/temporal", response_model=ClosedLoopTemporalResponse)
async def get_growth_closed_loop_temporal(
    project_id: UUID,
    published_at: str | None = Query(default=None),
    mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    horizon_days: int = Query(default=7, ge=1, le=30),
    max_actions: int = Query(default=5, ge=1, le=20),
    timezone: str = Query(default="UTC"),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ClosedLoopTemporalResponse:
    await get_accessible_project(db, project_id, user.id)
    data, saved = await _build_temporal_closed_loop_policy(
        db,
        project_id,
        published_at=published_at,
        sync_performance=False,
        save_recommendations=False,
        mode=mode,
        horizon_days=horizon_days,
        max_actions=max_actions,
        timezone=timezone,
        workflow_name=workflow_name,
        persist_report=False,
    )
    return ClosedLoopTemporalResponse(**data, recommendations_saved=saved)


@router.post("/autopilot/closed-loop/temporal/sync", response_model=ClosedLoopTemporalResponse)
async def sync_growth_closed_loop_temporal(
    project_id: UUID,
    published_at: str | None = Query(default=None),
    sync_performance: bool = Query(default=True),
    save_recommendations: bool = Query(default=True),
    mode: str = Query(default="assisted", pattern="^(manual|assisted|automatic|auto|assistido)$"),
    horizon_days: int = Query(default=7, ge=1, le=30),
    max_actions: int = Query(default=5, ge=1, le=20),
    timezone: str = Query(default="UTC"),
    workflow_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> ClosedLoopTemporalResponse:
    await _enforce_growth_rate_limit(user, "closed_loop_temporal_sync")
    await get_accessible_project(db, project_id, user.id)
    data, saved = await _build_temporal_closed_loop_policy(
        db,
        project_id,
        published_at=published_at,
        sync_performance=sync_performance,
        save_recommendations=save_recommendations,
        mode=mode,
        horizon_days=horizon_days,
        max_actions=max_actions,
        timezone=timezone,
        workflow_name=workflow_name,
        persist_report=True,
    )
    await db.commit()
    return ClosedLoopTemporalResponse(**data, recommendations_saved=saved)


@router.get("/social-autopilot/plan", response_model=SocialAutopilotPlanResponse)
async def get_growth_social_autopilot_plan(
    project_id: UUID,
    mode: str = Query(default="assisted", pattern="^(assisted|automatic|live|auto|assistido)$"),
    publish_authorized: bool = Query(default=False),
    horizon_days: int = Query(default=30, ge=1, le=90),
    max_operations: int = Query(default=8, ge=1, le=30),
    include_community: bool = Query(default=True),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SocialAutopilotPlanResponse:
    await get_accessible_project(db, project_id, user.id)
    service = _growth_service(db)
    report = await service.build_report(db, project_id, persist=False)
    calendar = await service.get_content_calendar(project_id, horizon_days=horizon_days)
    performance = await service.interpret_performance(db, project_id)
    community_signals: dict = {}
    if include_community:
        try:
            comment_rows = await list_comment_insights(db, project_id, limit=50)
            draft_rows = await list_community_drafts(db, project_id, limit=50)
            community_signals = build_community_intelligence_report(
                project_id=str(project_id),
                comment_insights=comment_rows,
                community_drafts=draft_rows,
            ).to_dict()
        except Exception:
            community_signals = {}
    plan = build_social_autopilot_plan(
        project_id=str(project_id),
        channels=[channel.to_dict() for channel in report.channels],
        calendar_items=calendar,
        performance_rows=performance.top_assets,
        community_signals=community_signals,
        mode=mode,
        publish_authorized=publish_authorized,
        max_operations=max_operations,
        actor_id=str(user.id),
    )
    return SocialAutopilotPlanResponse(**plan.to_dict())


@router.get("/social-autopilot/approval-queue", response_model=SocialApprovalQueueResponse)
async def get_growth_social_approval_queue(
    project_id: UUID,
    mode: str = Query(default="assisted", pattern="^(assisted|automatic|live|auto|assistido)$"),
    publish_authorized: bool = Query(default=False),
    horizon_days: int = Query(default=30, ge=1, le=90),
    max_operations: int = Query(default=8, ge=1, le=30),
    include_community: bool = Query(default=True),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SocialApprovalQueueResponse:
    await get_accessible_project(db, project_id, user.id)
    service = _growth_service(db)
    report = await service.build_report(db, project_id, persist=False)
    calendar = await service.get_content_calendar(project_id, horizon_days=horizon_days)
    performance = await service.interpret_performance(db, project_id)
    community_signals: dict = {}
    if include_community:
        try:
            comment_rows = await list_comment_insights(db, project_id, limit=50)
            draft_rows = await list_community_drafts(db, project_id, limit=50)
            community_signals = build_community_intelligence_report(
                project_id=str(project_id),
                comment_insights=comment_rows,
                community_drafts=draft_rows,
            ).to_dict()
        except Exception:
            community_signals = {}
    plan = build_social_autopilot_plan(
        project_id=str(project_id),
        channels=[channel.to_dict() for channel in report.channels],
        calendar_items=calendar,
        performance_rows=performance.top_assets,
        community_signals=community_signals,
        mode=mode,
        publish_authorized=publish_authorized,
        max_operations=max_operations,
        actor_id=str(user.id),
    )
    queue = build_social_approval_queue(
        project_id=str(project_id),
        operations=[item.to_dict() for item in [*plan.operations, *plan.blocked_operations]],
        governance_contract=plan.governance_contract,
        actor_id=str(user.id),
    )
    return SocialApprovalQueueResponse(**queue.to_dict())

@router.get("/social-autopilot/dispatch-plan", response_model=SocialDispatchPlanResponse)
async def get_growth_social_dispatch_plan(
    project_id: UUID,
    mode: str = Query(default="assisted", pattern="^(assisted|automatic|live|auto|assistido)$"),
    publish_authorized: bool = Query(default=False),
    execute: bool = Query(default=False),
    allow_review_items: bool = Query(default=False),
    horizon_days: int = Query(default=30, ge=1, le=90),
    max_operations: int = Query(default=8, ge=1, le=30),
    include_community: bool = Query(default=True),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SocialDispatchPlanResponse:
    await get_accessible_project(db, project_id, user.id)
    service = _growth_service(db)
    report = await service.build_report(db, project_id, persist=False)
    calendar = await service.get_content_calendar(project_id, horizon_days=horizon_days)
    performance = await service.interpret_performance(db, project_id)
    community_signals: dict = {}
    if include_community:
        try:
            comment_rows = await list_comment_insights(db, project_id, limit=50)
            draft_rows = await list_community_drafts(db, project_id, limit=50)
            community_signals = build_community_intelligence_report(
                project_id=str(project_id),
                comment_insights=comment_rows,
                community_drafts=draft_rows,
            ).to_dict()
        except Exception:
            community_signals = {}
    plan = build_social_autopilot_plan(
        project_id=str(project_id),
        channels=[channel.to_dict() for channel in report.channels],
        calendar_items=calendar,
        performance_rows=performance.top_assets,
        community_signals=community_signals,
        mode=mode,
        publish_authorized=publish_authorized,
        max_operations=max_operations,
        actor_id=str(user.id),
    )
    queue = build_social_approval_queue(
        project_id=str(project_id),
        operations=[item.to_dict() for item in [*plan.operations, *plan.blocked_operations]],
        governance_contract=plan.governance_contract,
        actor_id=str(user.id),
    )
    dispatch = build_social_dispatch_plan(
        project_id=str(project_id),
        queue_items=[item.to_dict() for item in queue.items],
        execute=execute,
        allow_review_items=allow_review_items,
        actor_id=str(user.id),
    )
    return SocialDispatchPlanResponse(**dispatch.to_dict())

@router.get("/social-autopilot/observability", response_model=SocialObservabilityResponse)
async def get_growth_social_observability(
    project_id: UUID,
    mode: str = Query(default="assisted", pattern="^(assisted|automatic|live|auto|assistido)$"),
    publish_authorized: bool = Query(default=False),
    execute: bool = Query(default=False),
    allow_review_items: bool = Query(default=False),
    horizon_days: int = Query(default=30, ge=1, le=90),
    max_operations: int = Query(default=8, ge=1, le=30),
    include_community: bool = Query(default=True),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SocialObservabilityResponse:
    await get_accessible_project(db, project_id, user.id)
    service = _growth_service(db)
    report = await service.build_report(db, project_id, persist=False)
    calendar = await service.get_content_calendar(project_id, horizon_days=horizon_days)
    performance = await service.interpret_performance(db, project_id)
    community_signals: dict = {}
    if include_community:
        try:
            comment_rows = await list_comment_insights(db, project_id, limit=50)
            draft_rows = await list_community_drafts(db, project_id, limit=50)
            community_signals = build_community_intelligence_report(
                project_id=str(project_id),
                comment_insights=comment_rows,
                community_drafts=draft_rows,
            ).to_dict()
        except Exception:
            community_signals = {}
    plan = build_social_autopilot_plan(
        project_id=str(project_id),
        channels=[channel.to_dict() for channel in report.channels],
        calendar_items=calendar,
        performance_rows=performance.top_assets,
        community_signals=community_signals,
        mode=mode,
        publish_authorized=publish_authorized,
        max_operations=max_operations,
        actor_id=str(user.id),
    )
    queue = build_social_approval_queue(
        project_id=str(project_id),
        operations=[item.to_dict() for item in [*plan.operations, *plan.blocked_operations]],
        governance_contract=plan.governance_contract,
        actor_id=str(user.id),
    )
    dispatch = build_social_dispatch_plan(
        project_id=str(project_id),
        queue_items=[item.to_dict() for item in queue.items],
        execute=execute,
        allow_review_items=allow_review_items,
        actor_id=str(user.id),
    )
    observability = build_social_observability_report(
        project_id=str(project_id),
        plan=plan.to_dict(),
        queue=queue.to_dict(),
        dispatch=dispatch.to_dict(),
    )
    return SocialObservabilityResponse(**observability.to_dict())

@router.get("/social-autopilot/learning", response_model=SocialLearningResponse)
async def get_growth_social_learning(
    project_id: UUID,
    mode: str = Query(default="assisted", pattern="^(assisted|automatic|live|auto|assistido)$"),
    publish_authorized: bool = Query(default=False),
    execute: bool = Query(default=False),
    allow_review_items: bool = Query(default=False),
    horizon_days: int = Query(default=30, ge=1, le=90),
    max_operations: int = Query(default=8, ge=1, le=30),
    include_community: bool = Query(default=True),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SocialLearningResponse:
    await get_accessible_project(db, project_id, user.id)
    service = _growth_service(db)
    report = await service.build_report(db, project_id, persist=False)
    calendar = await service.get_content_calendar(project_id, horizon_days=horizon_days)
    performance = await service.interpret_performance(db, project_id)
    community_signals: dict = {}
    if include_community:
        try:
            comment_rows = await list_comment_insights(db, project_id, limit=50)
            draft_rows = await list_community_drafts(db, project_id, limit=50)
            community_signals = build_community_intelligence_report(
                project_id=str(project_id),
                comment_insights=comment_rows,
                community_drafts=draft_rows,
            ).to_dict()
        except Exception:
            community_signals = {}
    plan = build_social_autopilot_plan(
        project_id=str(project_id),
        channels=[channel.to_dict() for channel in report.channels],
        calendar_items=calendar,
        performance_rows=performance.top_assets,
        community_signals=community_signals,
        mode=mode,
        publish_authorized=publish_authorized,
        max_operations=max_operations,
        actor_id=str(user.id),
    )
    queue = build_social_approval_queue(
        project_id=str(project_id),
        operations=[item.to_dict() for item in [*plan.operations, *plan.blocked_operations]],
        governance_contract=plan.governance_contract,
        actor_id=str(user.id),
    )
    dispatch = build_social_dispatch_plan(
        project_id=str(project_id),
        queue_items=[item.to_dict() for item in queue.items],
        execute=execute,
        allow_review_items=allow_review_items,
        actor_id=str(user.id),
    )
    observability = build_social_observability_report(
        project_id=str(project_id),
        plan=plan.to_dict(),
        queue=queue.to_dict(),
        dispatch=dispatch.to_dict(),
    )
    learning = build_social_learning_report(
        project_id=str(project_id),
        observability=observability.to_dict(),
        performance_rows=performance.top_assets,
        community_signals=community_signals,
    )
    return SocialLearningResponse(**learning.to_dict())
@router.get("/cost-intelligence", response_model=CostDecisionResponse)
async def get_growth_cost_intelligence(
    project_id: UUID,
    quantity: int = Query(default=1, ge=1, le=50),
    ai_video_percent: int = Query(default=0, ge=0, le=100),
    ai_image_percent: int = Query(default=0, ge=0, le=100),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CostDecisionResponse:
    project = await get_accessible_project(db, project_id, user.id)
    credits_balance: int | None = None
    monthly_quota = 0
    monthly_used = 0
    concurrent_limit = 0
    concurrent_active = 0

    if project.org_id:
        billing = await get_org_billing(db, project.org_id)
        credits_balance = billing.credits_balance if billing_enforced() else None
        quotas = await get_quota_status(db, project.org_id)
        monthly_quota = quotas.monthly_pipeline_quota
        monthly_used = quotas.monthly_pipelines_used
        concurrent_limit = quotas.max_concurrent_pipelines
        concurrent_active = quotas.concurrent_pipelines_active

    source_mix: list[dict] = []
    if ai_video_percent:
        source_mix.append({"source": "ai_video", "percentage": ai_video_percent})
    if ai_image_percent:
        source_mix.append({"source": "ai_image", "percentage": ai_image_percent})
    remaining = max(0, 100 - ai_video_percent - ai_image_percent)
    if remaining:
        source_mix.append({"source": "own_library", "percentage": remaining})

    decision = build_cost_decision_score(
        quantity=quantity,
        credit_cost_per_pipeline=pipeline_credit_cost(),
        credits_balance=credits_balance,
        monthly_quota=monthly_quota,
        monthly_used=monthly_used,
        concurrent_limit=concurrent_limit,
        concurrent_active=concurrent_active,
        media_strategy={"source_mix": source_mix},
    )
    data = decision.to_dict()
    if is_unlimited(monthly_quota):
        data["monthly_remaining"] = None
    return CostDecisionResponse(**data)



@router.get("/resource-readiness", response_model=ResourceReadinessResponse)
async def get_growth_resource_readiness(
    project_id: UUID,
    quantity: int = Query(default=1, ge=1, le=50),
    requires_gpu: bool = Query(default=False),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ResourceReadinessResponse:
    await get_accessible_project(db, project_id, user.id)
    system = collect_system_metrics()
    celery = await collect_celery_queues()
    gpu = system.gpu
    system_data = {
        "cpu": {"percent": system.cpu.percent, "cores": system.cpu.cores},
        "memory": {
            "used_mb": system.memory.used_mb,
            "total_mb": system.memory.total_mb,
            "percent": system.memory.percent,
        },
        "disk": {
            "used_gb": system.disk.used_gb,
            "total_gb": system.disk.total_gb,
            "percent": system.disk.percent,
        },
        "gpu": {
            "available": bool(gpu),
            "name": gpu.name if gpu else "",
            "utilization": gpu.utilization if gpu else 0.0,
            "memory_used_mb": gpu.memory_used_mb if gpu else 0.0,
            "memory_total_mb": gpu.memory_total_mb if gpu else 0.0,
        }
        if gpu
        else None,
    }
    readiness = build_resource_readiness(
        system_metrics=system_data,
        celery_metrics=celery,
        requires_gpu=requires_gpu,
        quantity=quantity,
    )
    return ResourceReadinessResponse(**readiness.to_dict())

@router.get("/performance", response_model=GrowthPerformanceResponse)
async def get_growth_performance(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GrowthPerformanceResponse:
    await get_accessible_project(db, project_id, user.id)
    interpretation = await _growth_service(db).interpret_performance(db, project_id)
    data = interpretation.to_dict()
    return GrowthPerformanceResponse(
        **{k: v for k, v in data.items() if k != "recommendations"},
        recommendations=[GrowthRecommendationResponse(**rec) for rec in data.get("recommendations") or []],
    )


@router.post("/performance/sync", response_model=GrowthPerformanceSyncResponse)
async def sync_growth_performance(
    project_id: UUID,
    persist: bool = Query(default=True),
    save_recommendations: bool = Query(default=True),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> GrowthPerformanceSyncResponse:
    await _enforce_growth_rate_limit(user, "performance_sync")
    await get_accessible_project(db, project_id, user.id)
    service = _growth_service(db)
    before_count = len(await service.list_recommendations(project_id))
    interpretation = await service.sync_performance_learning(
        db,
        project_id,
        persist=persist,
        save_recommendations=save_recommendations,
    )
    await db.commit()
    after_count = len(await service.list_recommendations(project_id))
    data = interpretation.to_dict()
    return GrowthPerformanceSyncResponse(
        interpretation=GrowthPerformanceResponse(
            **{k: v for k, v in data.items() if k != "recommendations"},
            recommendations=[GrowthRecommendationResponse(**rec) for rec in data.get("recommendations") or []],
        ),
        recommendations_saved=max(0, after_count - before_count),
    )


class GrowthHistoryEventResponse(BaseModel):
    id: str
    project_id: str
    channel_id: str | None = None
    kind: str
    title: str
    detail: str
    status: str
    occurred_at: str
    metadata: dict = Field(default_factory=dict)


@router.get("/history", response_model=list[GrowthHistoryEventResponse])
async def list_growth_history(
    project_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[GrowthHistoryEventResponse]:
    await get_accessible_project(db, project_id, user.id)
    events = await _growth_service(db).list_growth_history(db, project_id, limit=limit)
    return [GrowthHistoryEventResponse(**event.to_dict()) for event in events]


@router.get("/recommendations", response_model=list[GrowthRecommendationResponse])
async def get_growth_recommendations(
    project_id: UUID,
    channel_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[GrowthRecommendationResponse]:
    await get_accessible_project(db, project_id, user.id)
    if channel_id is not None:
        channel = await db.get(Channel, channel_id)
        if not channel or channel.project_id != project_id:
            raise HTTPException(status_code=404, detail="Channel not found in project")
    rows = await _growth_service(db).list_recommendations(project_id, channel_id=channel_id)
    return [GrowthRecommendationResponse(**row.to_dict()) for row in rows]


@router.get("/market-intelligence", response_model=MarketIntelligenceResponse)
async def get_market_intelligence(
    project_id: UUID,
    channel_id: UUID | None = Query(default=None),
    horizon_days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MarketIntelligenceResponse:
    await get_accessible_project(db, project_id, user.id)
    if channel_id is not None:
        channel = await db.get(Channel, channel_id)
        if not channel or channel.project_id != project_id:
            raise HTTPException(status_code=404, detail="Channel not found in project")
    provider = GrowthMarketIntelligenceProvider(_growth_service(db), db)
    report = await provider.build_report(
        str(project_id),
        channel_id=str(channel_id) if channel_id else None,
        horizon_days=horizon_days,
    )
    return MarketIntelligenceResponse(**report.to_dict())


@router.post("/market-intelligence/recommendations", response_model=MarketRecommendationSyncResponse)
async def sync_market_intelligence_recommendations(
    project_id: UUID,
    channel_id: UUID | None = Query(default=None),
    horizon_days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> MarketRecommendationSyncResponse:
    await _enforce_growth_rate_limit(user, "market_intelligence_sync")
    await get_accessible_project(db, project_id, user.id)
    if channel_id is not None:
        channel = await db.get(Channel, channel_id)
        if not channel or channel.project_id != project_id:
            raise HTTPException(status_code=404, detail="Channel not found in project")
    service = _growth_service(db)
    provider = GrowthMarketIntelligenceProvider(service, db)
    report = await provider.build_report(
        str(project_id),
        channel_id=str(channel_id) if channel_id else None,
        horizon_days=horizon_days,
    )
    recommendations = provider.recommendations_from_report(report)
    saved = await service.save_recommendations(project_id, recommendations)
    await db.commit()
    return MarketRecommendationSyncResponse(
        report=MarketIntelligenceResponse(**report.to_dict()),
        recommendations_saved=saved,
    )












