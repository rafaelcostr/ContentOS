"""SEO Engine API — V5.2.3."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.seo import SeoOptimizer
from contentos_intelligence.domain.seo_package import SeoPackage
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/seo", tags=["SEO Engine"])


class SeoOptimizeRequest(BaseModel):
    project_id: UUID
    topic: str = Field(default="", max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)


class PlatformSeoResponse(BaseModel):
    platform: str
    title: str
    description: str
    hashtags: list[str]


class SeoOptimizeResponse(BaseModel):
    title: str
    description: str
    hashtags: list[str]
    keywords: list[str]
    title_variants: list[str]
    platforms: dict[str, PlatformSeoResponse]
    seo_score: float
    recommendations: list[str]


@router.post("/optimize", response_model=SeoOptimizeResponse)
async def optimize_seo(
    body: SeoOptimizeRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> SeoOptimizeResponse:
    await get_accessible_project(db, body.project_id, user.id)
    payload = dict(body.payload)
    if body.topic and not payload.get("topic"):
        payload["topic"] = body.topic
    package = SeoOptimizer().optimize(payload)
    return _to_response(package)


def _to_response(package: SeoPackage) -> SeoOptimizeResponse:
    data = package.to_dict()
    platforms = {
        key: PlatformSeoResponse(
            platform=str(val.get("platform") or key),
            title=str(val.get("title") or ""),
            description=str(val.get("description") or ""),
            hashtags=list(val.get("hashtags") or []),
        )
        for key, val in (data.get("platforms") or {}).items()
        if isinstance(val, dict)
    }
    return SeoOptimizeResponse(
        title=package.title,
        description=package.description,
        hashtags=package.hashtags,
        keywords=package.keywords,
        title_variants=package.title_variants,
        platforms=platforms,
        seo_score=package.seo_score,
        recommendations=package.recommendations,
    )
