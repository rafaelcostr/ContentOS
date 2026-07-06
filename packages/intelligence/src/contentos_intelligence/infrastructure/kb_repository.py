"""Knowledge Base persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.domain.knowledge_entry import KnowledgeEntryData


def _row_to_data(row) -> KnowledgeEntryData:
    return KnowledgeEntryData(
        id=row.id,
        project_id=row.project_id,
        org_id=row.org_id,
        pipeline_id=row.pipeline_id,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        title=row.title or "",
        content_text=row.content_text or "",
        snippet=row.snippet or "",
        embedding=list(row.embedding or []),
        embedding_model=row.embedding_model or "",
        metadata=dict(row.metadata_ or {}),
        version=row.version or 1,
        parent_entry_id=row.parent_entry_id,
        created_at=row.created_at,
    )


class KnowledgeRepository:
    async def list_by_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        resource_type: str | None = None,
        limit: int = 50,
    ) -> list[KnowledgeEntryData]:
        from contentos_database.models import KnowledgeEntry

        stmt = select(KnowledgeEntry).where(KnowledgeEntry.project_id == project_id)
        if resource_type:
            stmt = stmt.where(KnowledgeEntry.resource_type == resource_type)
        stmt = stmt.order_by(desc(KnowledgeEntry.created_at)).limit(limit)
        result = await db.execute(stmt)
        return [_row_to_data(r) for r in result.scalars().all()]

    async def list_versions(
        self,
        db: AsyncSession,
        *,
        resource_type: str,
        resource_id: UUID,
    ) -> list[KnowledgeEntryData]:
        from contentos_database.models import KnowledgeEntry

        stmt = (
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.resource_type == resource_type,
                KnowledgeEntry.resource_id == resource_id,
            )
            .order_by(desc(KnowledgeEntry.version))
        )
        result = await db.execute(stmt)
        return [_row_to_data(r) for r in result.scalars().all()]

    async def get_latest(
        self,
        db: AsyncSession,
        *,
        resource_type: str,
        resource_id: UUID,
    ) -> KnowledgeEntryData | None:
        versions = await self.list_versions(db, resource_type=resource_type, resource_id=resource_id)
        return versions[0] if versions else None

    async def insert(self, db: AsyncSession, data: KnowledgeEntryData) -> KnowledgeEntryData:
        from contentos_database.models import KnowledgeEntry

        now = datetime.now(UTC)
        row = KnowledgeEntry(
            project_id=data.project_id,
            org_id=data.org_id,
            pipeline_id=data.pipeline_id,
            resource_type=data.resource_type,
            resource_id=data.resource_id,
            title=data.title,
            content_text=data.content_text,
            snippet=data.snippet,
            embedding=data.embedding or None,
            embedding_model=data.embedding_model or None,
            metadata_=data.metadata or None,
            version=data.version,
            parent_entry_id=data.parent_entry_id,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return _row_to_data(row)

    async def fetch_candidates(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        resource_types: list[str] | None = None,
        limit: int = 200,
    ) -> list[KnowledgeEntryData]:
        from contentos_database.models import KnowledgeEntry

        stmt = select(KnowledgeEntry).where(KnowledgeEntry.project_id == project_id)
        if resource_types:
            stmt = stmt.where(KnowledgeEntry.resource_type.in_(resource_types))
        stmt = stmt.order_by(desc(KnowledgeEntry.created_at)).limit(limit)
        result = await db.execute(stmt)
        return [_row_to_data(r) for r in result.scalars().all()]
