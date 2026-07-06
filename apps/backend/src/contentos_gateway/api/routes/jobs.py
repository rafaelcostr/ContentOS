from uuid import UUID

import httpx
from contentos_database.models import User
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.config import settings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobResponse(BaseModel):
    id: UUID
    pipeline_id: UUID
    step: str
    status: str
    order: int


@router.get("/pipeline/{pipeline_id}")
async def get_pipeline_jobs(
    pipeline_id: UUID,
    _user: User = Depends(get_current_user),
) -> list[JobResponse]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{settings.workflow_engine_url}/internal/pipelines/{pipeline_id}/jobs")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
