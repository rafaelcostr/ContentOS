"""Multi Content API — Epic 2a V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.multi_content import MultiContentService
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.multi_content import MultiContentReport
from contentos_intelligence.infrastructure.multi_content_repository import MultiContentRepository
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/multi-content", tags=["Multi Content"])


class MultiContentGenerateRequest(BaseModel):
    project_id: UUID
    topic: str = Field(min_length=1, max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)
    formats: list[str] | None = None
    persist: bool = True


class TextArtifactResponse(BaseModel):
    format: str
    title: str
    content: str
    data: dict = Field(default_factory=dict)
    source: str


class MultiContentReportResponse(BaseModel):
    project_id: str
    pipeline_id: str | None
    topic: str
    artifact_count: int
    artifacts: list[TextArtifactResponse]


@router.post("/generate", response_model=MultiContentReportResponse)
async def generate_multi_content(
    body: MultiContentGenerateRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> MultiContentReportResponse:
    await get_accessible_project(db, body.project_id, user.id)
    context = IntelligenceContext(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        topic=body.topic,
        payload=body.payload,
    )
    service = MultiContentService()
    report = service.generate(context, formats=body.formats)
    if body.persist and body.pipeline_id:
        await MultiContentRepository().save_report(db, report)
    return _to_response(report)


@router.get("/pipeline/{pipeline_id}", response_model=list[TextArtifactResponse])
async def list_multi_content_for_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[TextArtifactResponse]:
    from contentos_database.models import Pipeline
    from sqlalchemy import select

    pipeline = (await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await get_accessible_project(db, pipeline.project_id, user.id)
    rows = await MultiContentRepository().list_by_pipeline(db, pipeline_id)
    return [
        TextArtifactResponse(
            format=r["format"],
            title=r["title"],
            content=r["content"],
            data=r.get("data") or {},
            source=r.get("source") or "heuristic",
        )
        for r in rows
    ]


def _to_response(report: MultiContentReport) -> MultiContentReportResponse:
    d = report.to_dict()
    return MultiContentReportResponse(
        project_id=d["project_id"],
        pipeline_id=d.get("pipeline_id"),
        topic=d["topic"],
        artifact_count=d["artifact_count"],
        artifacts=[
            TextArtifactResponse(
                format=a["format"],
                title=a["title"],
                content=a["content"],
                data=a.get("data") or {},
                source=a.get("source", "heuristic"),
            )
            for a in d["artifacts"]
        ],
    )


class VideoVariantGenerateRequest(BaseModel):
    project_id: UUID
    topic: str = Field(min_length=1, max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)
    platforms: list[str] | None = None
    persist: bool = True


class CropSpecResponse(BaseModel):
    width: int
    height: int
    crop_bias: str
    max_duration_seconds: int
    safe_zone: str


class VideoPlatformVariantResponse(BaseModel):
    platform: str
    title: str
    description: str
    hashtags: list[str] = Field(default_factory=list)
    crop_spec: CropSpecResponse
    render_ref: dict | None = None
    data: dict = Field(default_factory=dict)
    source: str


class VideoVariantsReportResponse(BaseModel):
    project_id: str
    pipeline_id: str | None
    topic: str
    variant_count: int
    variants: list[VideoPlatformVariantResponse]


@router.post("/video-variants/generate", response_model=VideoVariantsReportResponse)
async def generate_video_variants(
    body: VideoVariantGenerateRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> VideoVariantsReportResponse:
    from contentos_intelligence.application.multi_content_video.service import MultiContentVideoService
    from contentos_intelligence.infrastructure.video_variants_repository import VideoVariantsRepository

    await get_accessible_project(db, body.project_id, user.id)
    context = IntelligenceContext(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        topic=body.topic,
        payload=body.payload,
    )
    report = MultiContentVideoService().generate(context, platforms=body.platforms)
    if body.persist and body.pipeline_id:
        await VideoVariantsRepository().save_report(db, report)
    return _video_report_to_response(report)


@router.get("/video-variants/pipeline/{pipeline_id}", response_model=list[VideoPlatformVariantResponse])
async def list_video_variants_for_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[VideoPlatformVariantResponse]:
    from contentos_database.models import Pipeline
    from contentos_intelligence.infrastructure.video_variants_repository import VideoVariantsRepository
    from sqlalchemy import select

    pipeline = (await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await get_accessible_project(db, pipeline.project_id, user.id)
    rows = await VideoVariantsRepository().list_by_pipeline(db, pipeline_id)
    return [_row_to_video_variant(r) for r in rows]


def _video_report_to_response(report) -> VideoVariantsReportResponse:
    d = report.to_dict()
    return VideoVariantsReportResponse(
        project_id=d["project_id"],
        pipeline_id=d.get("pipeline_id"),
        topic=d["topic"],
        variant_count=d["variant_count"],
        variants=[_variant_dict_to_response(v) for v in d["variants"]],
    )


def _variant_dict_to_response(v: dict) -> VideoPlatformVariantResponse:
    crop = v.get("crop_spec") or {}
    return VideoPlatformVariantResponse(
        platform=v["platform"],
        title=v["title"],
        description=v["description"],
        hashtags=list(v.get("hashtags") or []),
        crop_spec=CropSpecResponse(
            width=int(crop.get("width", 1080)),
            height=int(crop.get("height", 1920)),
            crop_bias=str(crop.get("crop_bias", "center")),
            max_duration_seconds=int(crop.get("max_duration_seconds", 60)),
            safe_zone=str(crop.get("safe_zone", "vertical_full")),
        ),
        render_ref=v.get("render_ref"),
        data=dict(v.get("metadata") or {}),
        source=v.get("source", "heuristic"),
    )


def _row_to_video_variant(r: dict) -> VideoPlatformVariantResponse:
    crop = r.get("crop_spec") or {}
    return VideoPlatformVariantResponse(
        platform=r["platform"],
        title=r["title"],
        description=r["description"],
        hashtags=list(r.get("hashtags") or []),
        crop_spec=CropSpecResponse(
            width=int(crop.get("width", 1080)),
            height=int(crop.get("height", 1920)),
            crop_bias=str(crop.get("crop_bias", "center")),
            max_duration_seconds=int(crop.get("max_duration_seconds", 60)),
            safe_zone=str(crop.get("safe_zone", "vertical_full")),
        ),
        render_ref=r.get("render_ref"),
        data=r.get("data") or {},
        source=r.get("source", "heuristic"),
    )
