"""Search project assets in PostgreSQL."""

from __future__ import annotations

import os
from uuid import UUID

from contentos_sources.domain.source_candidate import SourceAsset, SourceCandidate, SourceHealth
from contentos_sources.domain.source_query import SourceQuery


class OwnLibrarySource:
    source_id = "own_library"

    async def search(self, query: SourceQuery) -> list[SourceCandidate]:
        if not query.project_id:
            return []
        rows = _load_project_assets(query.project_id)
        terms = [t.lower() for t in (query.tags + [query.visual_hint, query.scene_label]) if t]
        candidates: list[SourceCandidate] = []
        for row in rows:
            hay = f"{row.get('filename','')} {row.get('key','')}".lower()
            score = 0.6
            if terms:
                hits = sum(1 for t in terms if t.lower() in hay)
                score = min(1.0, hits / len(terms))
            if score < 0.2 and terms:
                continue
            candidates.append(
                SourceCandidate(
                    source_id=self.source_id,
                    candidate_id=str(row["id"]),
                    title=row.get("filename") or row.get("key", ""),
                    score=score,
                    reason="Project asset library",
                    metadata=row,
                )
            )
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:10]

    async def fetch(self, candidate_id: str) -> SourceAsset:
        row = _load_asset_by_id(candidate_id)
        if not row:
            raise ValueError(f"Asset {candidate_id} not found")
        from minio import Minio

        client = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "contentos"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "contentos_secret"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        )
        import hashlib

        bucket = row["bucket"]
        key = row["key"]
        response = client.get_object(bucket, key)
        data = response.read()
        response.close()
        response.release_conn()
        return SourceAsset(
            source_id=self.source_id,
            candidate_id=candidate_id,
            data=data,
            filename=row.get("filename") or key.split("/")[-1],
            content_type=row.get("content_type") or "video/mp4",
            metadata=row,
            sha256=hashlib.sha256(data).hexdigest(),
        )

    async def health(self) -> SourceHealth:
        if not os.getenv("DATABASE_URL"):
            return SourceHealth(self.source_id, False, "DATABASE_URL not set")
        return SourceHealth(self.source_id, True, "PostgreSQL asset index")


def _load_project_assets(project_id: UUID) -> list[dict]:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return []
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import Asset
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            rows = session.execute(select(Asset).where(Asset.project_id == project_id).limit(50)).scalars().all()
            return [
                {
                    "id": str(r.id),
                    "key": r.object_key,
                    "bucket": r.bucket,
                    "filename": (r.metadata_ or {}).get("filename") or r.object_key.split("/")[-1],
                    "content_type": r.content_type,
                    "category": r.category,
                }
                for r in rows
            ]
    except Exception:
        return []


def _load_asset_by_id(asset_id: str) -> dict | None:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return None
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from uuid import UUID as UUIDType

        from contentos_database.models import Asset
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            row = session.get(Asset, UUIDType(asset_id))
            if not row:
                return None
            return {
                "id": str(row.id),
                "key": row.object_key,
                "bucket": row.bucket,
                "filename": (row.metadata_ or {}).get("filename") or row.object_key.split("/")[-1],
                "content_type": row.content_type,
                "category": row.category,
            }
    except Exception:
        return None
