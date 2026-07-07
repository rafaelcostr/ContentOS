"""Content Factory API — V5.3."""

from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

import httpx
from contentos_database.billing_credits import InsufficientCreditsError
from contentos_database.models import ContentBatch, ContentBatchStatus, Pipeline
from contentos_database.quota_service import QuotaExceededError
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.config import settings
from contentos_gateway.services.billing_service import consume_pipeline_credit, ensure_org_billing
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.content_factory import (
    assert_batch_can_start,
    build_batch_plan,
    create_content_batch,
    estimate_batch_cost,
    factory_enabled,
    mark_batch_publish_approved,
    pipeline_context_for_variant,
    refresh_batch_variant_statuses,
)
from contentos_intelligence.domain.content_batch import BatchVariant
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/factory", tags=["Content Factory"])


class BatchVariantResponse(BaseModel):
    index: int
    topic: str
    content_angle: str
    hook_hint: str
    pipeline_id: str | None = None
    pipeline_status: str | None = None


class BatchCostEstimateResponse(BaseModel):
    quantity: int
    credit_cost_per_pipeline: int
    total_credit_cost: int
    monthly_quota: int
    monthly_used: int
    monthly_remaining: int | None
    concurrent_limit: int
    concurrent_active: int
    quota_ok: bool
    credits_ok: bool


class ContentBatchResponse(BaseModel):
    id: UUID
    project_id: UUID
    org_id: UUID | None
    topic: str
    workflow_name: str | None
    quantity: int
    status: str
    require_approval: bool
    variants: list[BatchVariantResponse]
    estimated_credit_cost: int
    publish_approved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateBatchRequest(BaseModel):
    project_id: UUID
    topic: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(default=3, ge=1, le=24)
    workflow_name: str | None = Field(default=None, max_length=80)
    require_approval: bool | None = None
    angles: list[str] | None = None
    auto_start: bool = False


class EstimateBatchRequest(BaseModel):
    project_id: UUID
    quantity: int = Field(default=3, ge=1, le=24)


class PlanBatchRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(default=3, ge=1, le=24)
    workflow_name: str | None = None
    require_approval: bool | None = None
    angles: list[str] | None = None


class PlanBatchResponse(BaseModel):
    topic: str
    workflow_name: str | None
    quantity: int
    require_approval: bool
    variants: list[BatchVariantResponse]


def _batch_response(batch: ContentBatch) -> ContentBatchResponse:
    variants = [BatchVariantResponse(**BatchVariant.from_dict(v).to_dict()) for v in (batch.variants or [])]
    return ContentBatchResponse(
        id=batch.id,
        project_id=batch.project_id,
        org_id=batch.org_id,
        topic=batch.topic,
        workflow_name=batch.workflow_name,
        quantity=batch.quantity,
        status=batch.status.value,
        require_approval=batch.require_approval,
        variants=variants,
        estimated_credit_cost=batch.estimated_credit_cost,
        publish_approved_at=batch.publish_approved_at,
        created_at=batch.created_at,
    )


def _cost_response(estimate) -> BatchCostEstimateResponse:
    return BatchCostEstimateResponse(**estimate.to_dict())


@router.post("/plan", response_model=PlanBatchResponse)
async def plan_batch(body: PlanBatchRequest, user=Depends(get_current_user)) -> PlanBatchResponse:
    if not factory_enabled():
        raise HTTPException(status_code=503, detail="Content Factory disabled")
    plan = build_batch_plan(
        body.topic,
        body.quantity,
        workflow_name=body.workflow_name,
        require_approval=body.require_approval,
        angles=body.angles,
    )
    return PlanBatchResponse(
        topic=plan.topic,
        workflow_name=plan.workflow_name,
        quantity=plan.quantity,
        require_approval=plan.require_approval,
        variants=[BatchVariantResponse(**v.to_dict()) for v in plan.variants],
    )


@router.post("/batches/estimate", response_model=BatchCostEstimateResponse)
async def estimate_batch(
    body: EstimateBatchRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> BatchCostEstimateResponse:
    project = await get_accessible_project(db, body.project_id, user.id)
    estimate = await estimate_batch_cost(db, project.org_id, body.quantity)
    return _cost_response(estimate)


@router.post("/batches", response_model=ContentBatchResponse, status_code=201)
async def create_batch(
    body: CreateBatchRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> ContentBatchResponse:
    if not factory_enabled():
        raise HTTPException(status_code=503, detail="Content Factory disabled")
    project = await get_accessible_project(db, body.project_id, user.id)
    if project.org_id:
        await ensure_org_billing(db, project.org_id)
    batch, _plan = await create_content_batch(
        db,
        project_id=project.id,
        org_id=project.org_id,
        topic=body.topic,
        quantity=body.quantity,
        workflow_name=body.workflow_name,
        require_approval=body.require_approval,
        angles=body.angles,
        created_by_user_id=user.id,
    )
    await db.commit()
    await db.refresh(batch)
    if body.auto_start:
        return await start_batch(batch.id, db=db, user=user)
    return _batch_response(batch)


@router.get("/batches", response_model=list[ContentBatchResponse])
async def list_batches(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[ContentBatchResponse]:
    await get_accessible_project(db, project_id, user.id)
    result = await db.execute(
        select(ContentBatch)
        .where(ContentBatch.project_id == project_id)
        .order_by(ContentBatch.created_at.desc())
        .limit(50)
    )
    batches = result.scalars().all()
    out: list[ContentBatchResponse] = []
    for batch in batches:
        await refresh_batch_variant_statuses(db, batch)
        out.append(_batch_response(batch))
    await db.commit()
    return out


@router.get("/batches/{batch_id}", response_model=ContentBatchResponse)
async def get_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> ContentBatchResponse:
    batch = await _get_batch_for_user(db, batch_id, user.id)
    await refresh_batch_variant_statuses(db, batch)
    await db.commit()
    return _batch_response(batch)


@router.post("/batches/{batch_id}/start", response_model=ContentBatchResponse)
async def start_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> ContentBatchResponse:
    if not factory_enabled():
        raise HTTPException(status_code=503, detail="Content Factory disabled")
    batch = await _get_batch_for_user(db, batch_id, user.id)
    if batch.status not in (ContentBatchStatus.PLANNED,):
        raise HTTPException(status_code=409, detail=f"Batch cannot start from status {batch.status.value}")
    project = await get_accessible_project(db, batch.project_id, user.id)
    try:
        await assert_batch_can_start(db, project.org_id, batch.quantity)
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=429,
            detail={"error": "quota_exceeded", "kind": exc.kind, "limit": exc.limit, "current": exc.current},
        ) from exc
    except InsufficientCreditsError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits: have {exc.balance}, need {exc.required}",
        ) from exc

    variants = [BatchVariant.from_dict(v) for v in (batch.variants or [])]
    updated: list[dict] = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        for variant in variants:
            context = pipeline_context_for_variant(
                batch.id,
                variant,
                require_approval=batch.require_approval,
            )
            try:
                resp = await client.post(
                    f"{settings.workflow_engine_url}/internal/pipelines",
                    json={
                        "project_id": str(batch.project_id),
                        "topic": variant.topic,
                        "workflow_name": batch.workflow_name,
                        "context_json": context,
                        "auto_start": True,
                    },
                )
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=503, detail=f"Workflow engine unreachable: {exc}") from exc
            if resp.status_code != 201:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            pipeline_id = UUID(resp.json()["id"])
            variant.pipeline_id = str(pipeline_id)
            updated.append(variant.to_dict())

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

    batch.variants = updated
    batch.status = ContentBatchStatus.RUNNING
    await db.commit()
    await db.refresh(batch)
    return _batch_response(batch)


@router.post("/batches/{batch_id}/approve-publish", response_model=ContentBatchResponse)
async def approve_batch_publish(
    batch_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> ContentBatchResponse:
    batch = await _get_batch_for_user(db, batch_id, user.id)
    if not batch.require_approval:
        raise HTTPException(status_code=400, detail="Batch does not require publish approval")
    if batch.publish_approved_at:
        return _batch_response(batch)

    mark_batch_publish_approved(batch, user.id)
    variants = [BatchVariant.from_dict(v) for v in (batch.variants or [])]
    async with httpx.AsyncClient(timeout=120.0) as client:
        for variant in variants:
            if not variant.pipeline_id:
                continue
            context = pipeline_context_for_variant(
                batch.id,
                variant,
                require_approval=True,
                publish_approved=True,
            )
            try:
                resp = await client.patch(
                    f"{settings.workflow_engine_url}/internal/pipelines/{variant.pipeline_id}/context",
                    json={"context": context},
                )
                if resp.status_code != 200:
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)
                await client.post(
                    f"{settings.workflow_engine_url}/internal/pipelines/{variant.pipeline_id}/retry-step",
                    json={"step": "publisher"},
                )
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=503, detail=f"Workflow engine unreachable: {exc}") from exc

    await db.commit()
    await db.refresh(batch)
    return _batch_response(batch)


async def _get_batch_for_user(db: AsyncSession, batch_id: UUID, user_id: UUID) -> ContentBatch:
    batch = await db.get(ContentBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    await get_accessible_project(db, batch.project_id, user_id)
    return batch
