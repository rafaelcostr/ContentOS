"""Workflow Engine HTTP service — internal API for Gateway and agent callbacks."""

import os
from contextlib import asynccontextmanager
from uuid import UUID

from contentos_database.models import Job, Pipeline, Project
from contentos_database.quota_service import QuotaExceededError, assert_can_start_pipeline, quotas_enforced
from contentos_database.session import create_tables, get_session, init_db
from contentos_database.workflow_seed import ensure_workflow_templates
from contentos_events import EventBusPublisher
from contentos_shared.enums import JobStatus
from contentos_workflow.engine import WorkflowEngine
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://contentos:contentos_secret@postgres:5432/contentos")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from contentos_shared.telemetry import init_telemetry, instrument_fastapi, shutdown_telemetry

    init_telemetry("contentos-workflow-engine")
    instrument_fastapi(app)
    init_db(DATABASE_URL)
    await create_tables()
    from contentos_database.session import _session_factory

    if _session_factory:
        async with _session_factory() as db:
            await ensure_workflow_templates(db)
            await db.commit()
    yield
    shutdown_telemetry()


app = FastAPI(title="ContentOS Workflow Engine", version="0.1.0", lifespan=lifespan)


class CreatePipelineRequest(BaseModel):
    project_id: UUID
    topic: str
    workflow_name: str | None = None


class AgentCallbackRequest(BaseModel):
    job_id: UUID
    status: str
    output_data: dict | None = None
    artifacts: list | None = None
    logs: list[str] | None = None
    error: str | None = None


def get_engine(db: AsyncSession = Depends(get_session)) -> WorkflowEngine:
    return WorkflowEngine(db, EventBusPublisher())


@app.post("/internal/pipelines", status_code=201)
async def create_pipeline(
    body: CreatePipelineRequest,
    engine: WorkflowEngine = Depends(get_engine),
    db: AsyncSession = Depends(get_session),
):
    project = await db.get(Project, body.project_id)
    if project and project.org_id and quotas_enforced():
        try:
            await assert_can_start_pipeline(db, project.org_id)
        except QuotaExceededError as exc:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "quota_exceeded",
                    "kind": exc.kind,
                    "limit": exc.limit,
                    "current": exc.current,
                },
            ) from exc
    pipeline = await engine.create_pipeline(body.project_id, body.topic, body.workflow_name)
    await engine.start_pipeline(pipeline.id)
    return {"id": str(pipeline.id), "topic": pipeline.topic, "status": pipeline.status.value}


@app.post("/internal/callback")
async def agent_callback(body: AgentCallbackRequest, engine: WorkflowEngine = Depends(get_engine)):
    status = JobStatus(body.status)
    await engine.handle_agent_callback(
        job_id=body.job_id,
        status=status,
        output_data=body.output_data,
        error=body.error,
        logs=body.logs,
    )
    return {"ok": True}


@app.get("/internal/pipelines/{pipeline_id}/jobs")
async def get_jobs(pipeline_id: UUID, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Job).where(Job.pipeline_id == pipeline_id).order_by(Job.order))
    jobs = result.scalars().all()
    return [
        {"id": str(j.id), "pipeline_id": str(j.pipeline_id), "step": j.step, "status": j.status.value, "order": j.order}
        for j in jobs
    ]


@app.get("/internal/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: UUID, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {
        "id": str(pipeline.id),
        "project_id": str(pipeline.project_id),
        "topic": pipeline.topic,
        "workflow_name": pipeline.workflow_name,
        "status": pipeline.status.value,
        "current_step": pipeline.current_step,
        "error_message": pipeline.error_message,
    }


@app.post("/internal/pipelines/{pipeline_id}/cancel")
async def cancel_pipeline(pipeline_id: UUID, engine: WorkflowEngine = Depends(get_engine)):
    try:
        pipeline = await engine.cancel_pipeline(pipeline_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "id": str(pipeline.id),
        "status": pipeline.status.value,
        "current_step": pipeline.current_step,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "workflow-engine"}
