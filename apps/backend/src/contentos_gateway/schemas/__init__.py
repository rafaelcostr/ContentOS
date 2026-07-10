from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    org_id: UUID | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID | None = None
    name: str
    description: str | None
    created_at: datetime


class PipelineResponse(BaseModel):
    id: UUID
    project_id: UUID
    org_id: UUID | None = None
    topic: str
    workflow_name: str | None = None
    status: str
    current_step: str | None
    created_at: datetime


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    pipeline_id: UUID | None = None
    title: str
    description: str | None = None
    status: str
    duration_seconds: float | None
    width: int
    height: int
    fps: int
    render_asset_id: UUID | None = None
    thumb_asset_id: UUID | None = None
    hashtags: list | None = None
    platform_variants: dict | None = None
    created_at: datetime


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    object_key: str
    content_type: str
    size_bytes: int
    sha256: str | None = None
    tags: list[str] | None = None
    version: int = 1
    metadata_: dict | None = None
    created_at: datetime


class LogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent: str | None
    level: str
    message: str
    pipeline_id: UUID | None
    created_at: datetime
