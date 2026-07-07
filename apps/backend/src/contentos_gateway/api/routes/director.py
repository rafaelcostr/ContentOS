"""AI Director API — V5.2.4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.director import plan_director_decision
from contentos_intelligence.domain.director_decision import DirectorDecision
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/director", tags=["AI Director"])


class DirectorPlanRequest(BaseModel):
    project_id: UUID
    topic: str = Field(default="", max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)


class DirectorWeakSignalResponse(BaseModel):
    name: str
    score: float
    weight: float
    source: str


class DirectorPlanResponse(BaseModel):
    passed: bool
    overall_score: float
    min_score: float
    target: str
    retry_from: str
    reason: str
    action: str
    weak_signals: list[DirectorWeakSignalResponse]


@router.post("/plan", response_model=DirectorPlanResponse)
async def plan_director(
    body: DirectorPlanRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> DirectorPlanResponse:
    await get_accessible_project(db, body.project_id, user.id)
    payload = dict(body.payload)
    if body.topic and not payload.get("topic"):
        payload["topic"] = body.topic
    decision = plan_director_decision(payload)
    return _to_response(decision)


def _to_response(decision: DirectorDecision) -> DirectorPlanResponse:
    return DirectorPlanResponse(
        passed=decision.passed,
        overall_score=decision.overall_score,
        min_score=decision.min_score,
        target=decision.target,
        retry_from=decision.retry_from,
        reason=decision.reason,
        action=decision.action,
        weak_signals=[
            DirectorWeakSignalResponse(
                name=s.name,
                score=s.score,
                weight=s.weight,
                source=s.source,
            )
            for s in decision.weak_signals
        ],
    )
