"""Platform ops — SLO and runbooks (V5.5.3)."""

from __future__ import annotations

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.slo_service import build_slo_report
from contentos_intelligence.application.slo import get_runbook, list_runbooks
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/ops", tags=["Ops"])


class SloStatusResponse(BaseModel):
    id: str
    name: str
    state: str
    target: str
    current: str
    runbook_id: str
    message: str = ""


class SloSummaryResponse(BaseModel):
    ok: int
    warning: int
    critical: int


class SloReportResponse(BaseModel):
    evaluated_at: str
    items: list[SloStatusResponse]
    summary: SloSummaryResponse


class RunbookResponse(BaseModel):
    id: str
    title: str
    severity: str
    doc_path: str
    summary: str


@router.get("/slo", response_model=SloReportResponse)
async def get_slo_report(
    db: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
) -> SloReportResponse:
    report = await build_slo_report(db)
    data = report.to_dict()
    return SloReportResponse(
        evaluated_at=data["evaluated_at"],
        items=[SloStatusResponse(**item) for item in data["items"]],
        summary=SloSummaryResponse(**data["summary"]),
    )


@router.get("/runbooks", response_model=list[RunbookResponse])
async def get_runbooks(
    _user=Depends(get_current_user),
) -> list[RunbookResponse]:
    return [RunbookResponse(**rb) for rb in list_runbooks()]


@router.get("/runbooks/{runbook_id}", response_model=RunbookResponse)
async def get_runbook_detail(
    runbook_id: str,
    _user=Depends(get_current_user),
) -> RunbookResponse:
    rb = get_runbook(runbook_id)
    if not rb:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return RunbookResponse(**rb)
