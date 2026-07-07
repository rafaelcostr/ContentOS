from typing import Any
from uuid import UUID

from contentos_database.models import User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.schemas import AssetResponse
from contentos_gateway.services.asset_service import AssetService
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/assets", tags=["Assets"])


class TagAssetRequest(BaseModel):
    tags: list[str]


class RecommendTakesRequest(BaseModel):
    topic: str
    scenes: list[dict[str, Any]] = Field(default_factory=list)


class RecommendTakesResponse(BaseModel):
    asset_matches: list[dict[str, Any]]
    assets_selected: list[dict[str, Any]]
    take_recommendation: bool
    asset_count: int


class AssetSemanticSearchHit(BaseModel):
    similarity: float
    match_type: str
    analysis: dict[str, Any] | None = None
    asset: AssetResponse


class AssetSemanticSearchResponse(BaseModel):
    query: str
    count: int
    semantic_search_enabled: bool
    results: list[AssetSemanticSearchHit]


class AssetPreviewResponse(BaseModel):
    asset_id: str
    url: str | None
    content_type: str
    expires_in: int
    kind: str
    available: bool
    error: str | None = None



@router.get("", response_model=list[AssetResponse])
async def list_assets(
    category: str | None = None,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[AssetResponse]:
    service = AssetService(db)
    assets = await service.list_assets(category=category)
    return [AssetResponse.model_validate(a) for a in assets]


@router.get("/search", response_model=list[AssetResponse])
async def search_assets(
    q: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    theme: str | None = None,
    game: str | None = None,
    character: str | None = None,
    motion: str | None = None,
    color: str | None = None,
    objects: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[AssetResponse]:
    service = AssetService(db)
    assets = await service.search_assets(
        q=q,
        category=category,
        tag=tag,
        theme=theme,
        game=game,
        character=character,
        motion=motion,
        color=color,
        objects=objects,
        limit=limit,
    )
    return [AssetResponse.model_validate(a) for a in assets]


@router.get("/search/semantic", response_model=AssetSemanticSearchResponse)
async def search_assets_semantic(
    q: str,
    category: str | None = None,
    limit: int = 50,
    min_similarity: float | None = None,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> AssetSemanticSearchResponse:
    """Semantic asset search via media embeddings (V5.0.6)."""
    service = AssetService(db)
    stats = await service.semantic_search_stats()
    hits = await service.search_assets_semantic(
        q,
        category=category,
        limit=min(max(limit, 1), 100),
        min_similarity=min_similarity,
    )
    results = [
        AssetSemanticSearchHit(
            similarity=item["similarity"],
            match_type=item["match_type"],
            analysis=item.get("analysis"),
            asset=AssetResponse.model_validate(item["asset"]),
        )
        for item in hits
    ]
    return AssetSemanticSearchResponse(
        query=q,
        count=len(results),
        semantic_search_enabled=stats["semantic_search_enabled"],
        results=results,
    )


@router.post("/recommend", response_model=RecommendTakesResponse)
async def recommend_takes(
    body: RecommendTakesRequest,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> RecommendTakesResponse:
    """Rank indexed video takes for planned scenes (V5.0.4)."""
    service = AssetService(db)
    result = await service.recommend_takes(topic=body.topic, scenes=body.scenes)
    return RecommendTakesResponse(**result)


@router.get("/{asset_id}/preview", response_model=AssetPreviewResponse)
async def get_asset_preview(
    asset_id: UUID,
    expires: int = 3600,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> AssetPreviewResponse:
    """Presigned MinIO URL for browser preview (rewritten to public endpoint)."""
    service = AssetService(db)
    preview = await service.get_preview(asset_id, expires=min(max(expires, 60), 86400))
    if not preview:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetPreviewResponse(**preview)


@router.get("/{asset_id}/content")
async def get_asset_content(
    asset_id: UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> Response:
    """Authenticated byte stream — reliable dashboard preview without MinIO CORS."""
    service = AssetService(db)
    result = await service.get_content(asset_id)
    if not result:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset, data = result
    return Response(
        content=data,
        media_type=asset.content_type or "application/octet-stream",
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'inline; filename="{asset.object_key.split("/")[-1]}"',
        },
    )


@router.post("/{asset_id}/tags", response_model=AssetResponse)
async def tag_asset(
    asset_id: UUID,
    body: TagAssetRequest,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_editor()),
) -> AssetResponse:
    service = AssetService(db)
    asset = await service.tag_asset(asset_id, body.tags)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    await db.commit()
    return AssetResponse.model_validate(asset)


@router.get("/index/stats")
async def asset_index_stats(
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict:
    service = AssetService(db)
    stats = await service.index_stats()
    storage = await service.storage_stats()
    semantic = await service.semantic_search_stats()
    return {**stats, **storage, **semantic}


@router.post("/takes/upload", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_take(
    theme: str = Form(...),
    label: str = Form(...),
    file: UploadFile = File(...),
    project_id: UUID | None = Form(None),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_editor()),
) -> AssetResponse:
    service = AssetService(db)
    content = await file.read()
    asset = await service.upload_take(
        data=content,
        filename=file.filename or f"{label}.mp4",
        theme=theme,
        label=label,
        project_id=project_id,
    )
    return AssetResponse.model_validate(asset)


@router.get("/storage/stats")
async def storage_stats(
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict:
    service = AssetService(db)
    return await service.storage_stats()
