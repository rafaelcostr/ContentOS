"""Batch production service — V5.3.1."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from contentos_intelligence.application.content_factory.variation import plan_variations
from contentos_intelligence.domain.content_batch import BatchCostEstimate, BatchPlan, BatchVariant

try:
    from contentos_database.billing_credits import InsufficientCreditsError, billing_enforced, pipeline_credit_cost
    from contentos_database.models import ContentBatch, ContentBatchStatus, Pipeline, PipelineStatus, Project
    from contentos_database.quota_service import (
        QuotaExceededError,
        assert_can_start_batch,
        get_quota_status,
        is_unlimited,
    )
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover - unit tests without DB
    AsyncSession = object  # type: ignore[misc, assignment]
    ContentBatch = ContentBatchStatus = Pipeline = PipelineStatus = Project = object  # type: ignore[misc, assignment]
    InsufficientCreditsError = QuotaExceededError = Exception  # type: ignore[misc, assignment]


def factory_enabled() -> bool:
    return os.getenv("CONTENT_FACTORY_ENABLED", "true").lower() in ("1", "true", "yes")


def factory_default_require_approval() -> bool:
    return os.getenv("FACTORY_REQUIRE_APPROVAL", "false").lower() in ("1", "true", "yes")


def factory_max_batch_size() -> int:
    try:
        return max(1, min(24, int(os.getenv("FACTORY_MAX_BATCH_SIZE", "12"))))
    except ValueError:
        return 12


def build_batch_plan(
    topic: str,
    quantity: int,
    *,
    workflow_name: str | None = None,
    require_approval: bool | None = None,
    angles: list[str] | None = None,
) -> BatchPlan:
    qty = max(1, min(int(quantity), factory_max_batch_size()))
    approval = factory_default_require_approval() if require_approval is None else bool(require_approval)
    variants = plan_variations(topic, qty, angles=angles)
    return BatchPlan(
        topic=topic.strip(),
        workflow_name=workflow_name,
        quantity=qty,
        require_approval=approval,
        variants=variants,
    )


async def estimate_batch_cost(db: AsyncSession, org_id: UUID | None, quantity: int) -> BatchCostEstimate:
    qty = max(1, int(quantity))
    per = pipeline_credit_cost()
    total = per * qty
    if not org_id:
        return BatchCostEstimate(
            quantity=qty,
            credit_cost_per_pipeline=per,
            total_credit_cost=total,
            monthly_quota=0,
            monthly_used=0,
            monthly_remaining=None,
            concurrent_limit=0,
            concurrent_active=0,
            quota_ok=True,
            credits_ok=True,
        )
    status = await get_quota_status(db, org_id)
    monthly_remaining = None
    quota_ok = True
    if not is_unlimited(status.monthly_pipeline_quota):
        monthly_remaining = max(0, status.monthly_pipeline_quota - status.monthly_pipelines_used)
        quota_ok = status.monthly_pipelines_used + qty <= status.monthly_pipeline_quota
    if not is_unlimited(status.max_concurrent_pipelines):
        quota_ok = quota_ok and status.concurrent_pipelines_active + qty <= status.max_concurrent_pipelines
    credits_ok = True
    if billing_enforced():
        from contentos_database.models import OrganizationBilling

        billing = await db.get(OrganizationBilling, org_id)
        balance = billing.credits_balance if billing else 0
        credits_ok = balance >= total
    return BatchCostEstimate(
        quantity=qty,
        credit_cost_per_pipeline=per,
        total_credit_cost=total,
        monthly_quota=status.monthly_pipeline_quota,
        monthly_used=status.monthly_pipelines_used,
        monthly_remaining=monthly_remaining,
        concurrent_limit=status.max_concurrent_pipelines,
        concurrent_active=status.concurrent_pipelines_active,
        quota_ok=quota_ok,
        credits_ok=credits_ok,
    )


def pipeline_context_for_variant(
    batch_id: UUID,
    variant: BatchVariant,
    *,
    require_approval: bool,
    publish_approved: bool = False,
) -> dict[str, Any]:
    return {
        "content_angle": variant.content_angle,
        "hook_hint": variant.hook_hint,
        "factory_batch_id": str(batch_id),
        "factory_batch_index": variant.index,
        "factory_publish_hold": require_approval and not publish_approved,
        "factory_publish_approved": publish_approved,
    }


async def create_content_batch(
    db: AsyncSession,
    *,
    project_id: UUID,
    org_id: UUID | None,
    topic: str,
    quantity: int,
    workflow_name: str | None,
    require_approval: bool | None,
    angles: list[str] | None,
    created_by_user_id: UUID,
) -> tuple[ContentBatch, BatchPlan]:
    plan = build_batch_plan(
        topic,
        quantity,
        workflow_name=workflow_name,
        require_approval=require_approval,
        angles=angles,
    )
    estimate = await estimate_batch_cost(db, org_id, plan.quantity)
    plan.cost_estimate = estimate
    batch = ContentBatch(
        project_id=project_id,
        org_id=org_id,
        topic=plan.topic,
        workflow_name=plan.workflow_name,
        quantity=plan.quantity,
        status=ContentBatchStatus.PLANNED,
        require_approval=plan.require_approval,
        variants=[v.to_dict() for v in plan.variants],
        estimated_credit_cost=estimate.total_credit_cost,
        created_by_user_id=created_by_user_id,
    )
    db.add(batch)
    await db.flush()
    return batch, plan


async def assert_batch_can_start(db: AsyncSession, org_id: UUID | None, quantity: int) -> BatchCostEstimate:
    estimate = await estimate_batch_cost(db, org_id, quantity)
    if org_id:
        await assert_can_start_batch(db, org_id, quantity)
        if billing_enforced() and not estimate.credits_ok:
            from contentos_database.models import OrganizationBilling

            billing = await db.get(OrganizationBilling, org_id)
            balance = billing.credits_balance if billing else 0
            raise InsufficientCreditsError(balance, estimate.total_credit_cost)
    return estimate


async def refresh_batch_variant_statuses(db: AsyncSession, batch: ContentBatch) -> ContentBatch:
    variants = [BatchVariant.from_dict(v) for v in (batch.variants or [])]
    pipeline_ids = [UUID(v.pipeline_id) for v in variants if v.pipeline_id]
    if not pipeline_ids:
        return batch
    result = await db.execute(select(Pipeline).where(Pipeline.id.in_(pipeline_ids)))
    by_id = {str(p.id): p for p in result.scalars().all()}
    for variant in variants:
        if variant.pipeline_id and variant.pipeline_id in by_id:
            variant.pipeline_status = by_id[variant.pipeline_id].status.value
    batch.variants = [v.to_dict() for v in variants]
    await _sync_batch_status(db, batch)
    await db.flush()
    return batch


async def _sync_batch_status(db: AsyncSession, batch: ContentBatch) -> None:
    variants = [BatchVariant.from_dict(v) for v in (batch.variants or [])]
    if not variants or not any(v.pipeline_id for v in variants):
        return
    statuses = [v.pipeline_status for v in variants if v.pipeline_status]
    if not statuses:
        return
    if all(s == PipelineStatus.COMPLETED.value for s in statuses):
        if batch.require_approval and not batch.publish_approved_at:
            batch.status = ContentBatchStatus.PENDING_PUBLISH_APPROVAL
        else:
            batch.status = ContentBatchStatus.COMPLETED
    elif any(s == PipelineStatus.FAILED.value for s in statuses):
        if all(s in (PipelineStatus.COMPLETED.value, PipelineStatus.FAILED.value, PipelineStatus.CANCELLED.value) for s in statuses):
            batch.status = ContentBatchStatus.FAILED
    elif any(s in (PipelineStatus.PENDING.value, PipelineStatus.RUNNING.value) for s in statuses):
        batch.status = ContentBatchStatus.RUNNING


async def mark_batch_publish_approved(batch: ContentBatch, user_id: UUID) -> None:
    from datetime import datetime, timezone

    batch.publish_approved_at = datetime.now(timezone.utc)
    batch.publish_approved_by_user_id = user_id
    if batch.status == ContentBatchStatus.PENDING_PUBLISH_APPROVAL:
        batch.status = ContentBatchStatus.RUNNING
