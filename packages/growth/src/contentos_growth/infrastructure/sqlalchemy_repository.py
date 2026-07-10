"""SQLAlchemy repository for Growth AI."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_growth.domain import ChannelProfile, CompetitorProfile, GrowthRecommendation, GrowthStrategy


class SqlAlchemyGrowthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_channel_profiles(self, project_id: UUID) -> list[ChannelProfile]:
        from contentos_database.models import Channel, GrowthChannelProfileRow

        rows = (
            await self._db.execute(
                select(Channel, GrowthChannelProfileRow)
                .outerjoin(GrowthChannelProfileRow, GrowthChannelProfileRow.channel_id == Channel.id)
                .where(Channel.project_id == project_id)
                .order_by(Channel.created_at.desc())
            )
        ).all()
        return [
            ChannelProfile(
                channel_id=str(channel.id),
                project_id=str(channel.project_id),
                platform=channel.platform,
                name=channel.name,
                score=float(profile.score) if profile else 0.0,
                profile=dict(profile.profile_data or {}) if profile else {},
                report=dict(profile.report or {}) if profile else {},
                analyzed_at=profile.analyzed_at.isoformat() if profile and profile.analyzed_at else None,
                is_active=bool(channel.is_active),
                has_credentials=bool(channel.credentials),
            )
            for channel, profile in rows
        ]

    async def get_channel_profile(self, channel_id: UUID) -> ChannelProfile | None:
        from contentos_database.models import Channel, GrowthChannelProfileRow

        row = (
            await self._db.execute(
                select(Channel, GrowthChannelProfileRow)
                .outerjoin(GrowthChannelProfileRow, GrowthChannelProfileRow.channel_id == Channel.id)
                .where(Channel.id == channel_id)
            )
        ).first()
        if not row:
            return None
        channel, profile = row
        if not profile:
            return ChannelProfile(
                channel_id=str(channel.id),
                project_id=str(channel.project_id),
                platform=channel.platform,
                name=channel.name,
                is_active=bool(channel.is_active),
                has_credentials=bool(channel.credentials),
            )
        return ChannelProfile(
            channel_id=str(channel.id),
            project_id=str(channel.project_id),
            platform=channel.platform,
            name=channel.name,
            score=float(profile.score),
            profile=dict(profile.profile_data or {}),
            report=dict(profile.report or {}),
            analyzed_at=profile.analyzed_at.isoformat() if profile.analyzed_at else None,
            is_active=bool(channel.is_active),
            has_credentials=bool(channel.credentials),
        )

    async def save_channel_analysis(
        self,
        *,
        project_id: UUID,
        channel_id: UUID,
        score: float,
        profile_data: dict,
        report: dict,
        recommendations: list[GrowthRecommendation],
        summary: str,
    ) -> ChannelProfile:
        from datetime import datetime, timezone

        from contentos_database.models import Channel, GrowthChannelProfileRow, GrowthRecommendationRow, GrowthReportRow

        channel = (
            await self._db.execute(select(Channel).where(Channel.id == channel_id, Channel.project_id == project_id))
        ).scalar_one_or_none()
        if not channel:
            raise ValueError("Channel not found")

        now = datetime.now(timezone.utc)
        existing = (
            await self._db.execute(select(GrowthChannelProfileRow).where(GrowthChannelProfileRow.channel_id == channel_id))
        ).scalar_one_or_none()
        if existing:
            existing.score = score
            existing.profile_data = profile_data
            existing.report = report
            existing.analyzed_at = now
            existing.updated_at = now
            profile_row = existing
        else:
            profile_row = GrowthChannelProfileRow(
                id=uuid.uuid4(),
                project_id=project_id,
                channel_id=channel_id,
                score=score,
                profile_data=profile_data,
                report=report,
                analyzed_at=now,
                created_at=now,
                updated_at=now,
            )
            self._db.add(profile_row)

        self._db.add(
            GrowthReportRow(
                id=uuid.uuid4(),
                project_id=project_id,
                channel_id=channel_id,
                score=score,
                summary=summary,
                report=report,
                created_at=now,
            )
        )

        for rec in recommendations:
            self._db.add(
                GrowthRecommendationRow(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    channel_id=channel_id,
                    kind=rec.kind,
                    title=rec.title,
                    detail=rec.detail,
                    priority=rec.priority,
                    source=rec.source,
                    status=rec.status,
                    created_at=now,
                )
            )

        await self._db.flush()
        return ChannelProfile(
            channel_id=str(channel.id),
            project_id=str(channel.project_id),
            platform=channel.platform,
            name=channel.name,
            score=score,
            profile=dict(profile_data),
            report=dict(report),
            analyzed_at=now.isoformat(),
            is_active=bool(channel.is_active),
            has_credentials=bool(channel.credentials),
        )

    async def list_channel_analysis_history(self, channel_id: UUID, *, limit: int = 20) -> list[dict]:
        from contentos_database.models import GrowthReportRow

        rows = (
            await self._db.execute(
                select(GrowthReportRow)
                .where(GrowthReportRow.channel_id == channel_id)
                .order_by(desc(GrowthReportRow.created_at))
                .limit(min(limit, 100))
            )
        ).scalars().all()
        return [
            {
                "id": str(row.id),
                "channel_id": str(row.channel_id) if row.channel_id else None,
                "project_id": str(row.project_id),
                "score": row.score,
                "summary": row.summary,
                "report": dict(row.report or {}),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    async def list_competitors(self, project_id: UUID) -> list[CompetitorProfile]:
        from contentos_database.models import GrowthCompetitorRow

        result = await self._db.execute(
            select(GrowthCompetitorRow)
            .where(GrowthCompetitorRow.project_id == project_id)
            .order_by(desc(GrowthCompetitorRow.created_at))
        )
        return [_competitor_from_row(row) for row in result.scalars().all()]

    async def create_competitor(
        self,
        project_id: UUID,
        *,
        platform: str,
        handle: str,
        display_name: str,
        url: str | None = None,
        notes: str = "",
    ) -> CompetitorProfile:
        from contentos_database.models import GrowthCompetitorRow

        row = GrowthCompetitorRow(
            id=uuid.uuid4(),
            project_id=project_id,
            platform=platform,
            handle=handle,
            display_name=display_name,
            url=url,
            notes=notes,
            metrics={},
        )
        self._db.add(row)
        await self._db.flush()
        return _competitor_from_row(row)

    async def get_competitor(self, competitor_id: UUID) -> CompetitorProfile | None:
        from contentos_database.models import GrowthCompetitorRow

        row = (
            await self._db.execute(select(GrowthCompetitorRow).where(GrowthCompetitorRow.id == competitor_id))
        ).scalar_one_or_none()
        return _competitor_from_row(row) if row else None

    async def update_competitor(
        self,
        competitor_id: UUID,
        *,
        metrics: dict | None = None,
        display_name: str | None = None,
        url: str | None = None,
    ) -> CompetitorProfile:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthCompetitorRow

        row = (
            await self._db.execute(select(GrowthCompetitorRow).where(GrowthCompetitorRow.id == competitor_id))
        ).scalar_one_or_none()
        if not row:
            raise ValueError("Competitor not found")
        if metrics is not None:
            row.metrics = metrics
        if display_name:
            row.display_name = display_name
        if url:
            row.url = url
        row.updated_at = datetime.now(timezone.utc)
        await self._db.flush()
        return _competitor_from_row(row)

    async def save_competitor_recommendations(
        self,
        *,
        project_id: UUID,
        competitor_id: UUID,
        recommendations: list[GrowthRecommendation],
    ) -> None:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthRecommendationRow

        now = datetime.now(timezone.utc)
        for rec in recommendations:
            self._db.add(
                GrowthRecommendationRow(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    channel_id=None,
                    kind=rec.kind,
                    title=rec.title,
                    detail=rec.detail,
                    priority=rec.priority,
                    source=rec.source,
                    status=rec.status,
                    created_at=now,
                )
            )
        await self._db.flush()

    async def list_recommendations(
        self,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
    ) -> list[GrowthRecommendation]:
        from contentos_database.models import GrowthRecommendationRow

        query = select(GrowthRecommendationRow).where(GrowthRecommendationRow.project_id == project_id)
        if channel_id is not None:
            query = query.where(
                (GrowthRecommendationRow.channel_id == channel_id) | (GrowthRecommendationRow.channel_id.is_(None))
            )
        result = await self._db.execute(query.order_by(desc(GrowthRecommendationRow.created_at)).limit(50))
        return [
            GrowthRecommendation(
                id=str(row.id),
                project_id=str(row.project_id),
                channel_id=str(row.channel_id) if row.channel_id else None,
                kind=row.kind,
                title=row.title,
                detail=row.detail,
                priority=row.priority,
                source=row.source,
                status=row.status,
                created_at=row.created_at.isoformat() if row.created_at else None,
            )
            for row in result.scalars().all()
        ]

    async def save_recommendations(self, project_id: UUID, recommendations: list[GrowthRecommendation]) -> int:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthRecommendationRow

        if not recommendations:
            return 0
        existing = await self.list_recommendations(project_id)
        seen = {(rec.source, rec.title) for rec in existing}
        now = datetime.now(timezone.utc)
        saved = 0
        for rec in recommendations:
            key = (rec.source, rec.title)
            if key in seen:
                continue
            seen.add(key)
            self._db.add(
                GrowthRecommendationRow(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    channel_id=UUID(str(rec.channel_id)) if rec.channel_id else None,
                    kind=rec.kind,
                    title=rec.title,
                    detail=rec.detail,
                    priority=rec.priority,
                    source=rec.source,
                    status=rec.status,
                    created_at=now,
                )
            )
            saved += 1
        if saved:
            await self._db.flush()
        return saved

    async def get_strategy(
        self,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
    ) -> GrowthStrategy | None:
        from contentos_database.models import GrowthStrategyRow

        if channel_id is not None:
            row = (
                await self._db.execute(
                    select(GrowthStrategyRow)
                    .where(
                        GrowthStrategyRow.project_id == project_id,
                        GrowthStrategyRow.channel_id == channel_id,
                    )
                    .order_by(desc(GrowthStrategyRow.updated_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if row:
                return self._strategy_from_row(row)

        row = (
            await self._db.execute(
                select(GrowthStrategyRow)
                .where(
                    GrowthStrategyRow.project_id == project_id,
                    GrowthStrategyRow.channel_id.is_(None),
                )
                .order_by(desc(GrowthStrategyRow.updated_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if not row:
            row = (
                await self._db.execute(
                    select(GrowthStrategyRow)
                    .where(GrowthStrategyRow.project_id == project_id)
                    .order_by(desc(GrowthStrategyRow.updated_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
        if not row:
            return None
        return self._strategy_from_row(row)

    def _strategy_from_row(self, row) -> GrowthStrategy:
        return GrowthStrategy(
            project_id=str(row.project_id),
            channel_id=str(row.channel_id) if row.channel_id else None,
            positioning=str((row.kpis or {}).get("positioning") or ""),
            goals=list(row.goals or []),
            kpis=dict(row.kpis or {}),
            cadence=dict(row.cadence or {}),
            id=str(row.id),
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    async def save_strategy(self, project_id: UUID, strategy: GrowthStrategy, *, status: str = "active") -> GrowthStrategy:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthStrategyRow

        now = datetime.now(timezone.utc)
        channel_id = UUID(strategy.channel_id) if strategy.channel_id else None
        kpis = dict(strategy.kpis or {})
        if strategy.positioning:
            kpis["positioning"] = strategy.positioning
        cadence = dict(strategy.cadence or {})
        if cadence.get("campaigns"):
            cadence["campaigns"] = cadence["campaigns"]
        if cadence.get("channel_goals"):
            cadence["channel_goals"] = cadence["channel_goals"]

        row = GrowthStrategyRow(
            id=uuid.uuid4(),
            project_id=project_id,
            channel_id=channel_id,
            status=status,
            goals=list(strategy.goals or []),
            kpis=kpis or None,
            cadence=cadence or None,
            created_at=now,
            updated_at=now,
        )
        self._db.add(row)
        await self._db.flush()
        return GrowthStrategy(
            project_id=str(row.project_id),
            channel_id=str(row.channel_id) if row.channel_id else None,
            positioning=str((row.kpis or {}).get("positioning") or ""),
            goals=list(row.goals or []),
            kpis=dict(row.kpis or {}),
            cadence=dict(row.cadence or {}),
            id=str(row.id),
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    async def list_calendar_items(
        self,
        project_id: UUID,
        *,
        horizon_days: int = 30,
        channel_id: UUID | None = None,
    ) -> list[dict]:
        from datetime import datetime, timedelta, timezone

        from contentos_database.models import GrowthContentCalendarRow

        since = datetime.now(timezone.utc) - timedelta(days=1)
        until = datetime.now(timezone.utc) + timedelta(days=horizon_days)
        query = select(GrowthContentCalendarRow).where(
            GrowthContentCalendarRow.project_id == project_id,
            GrowthContentCalendarRow.planned_for >= since,
            GrowthContentCalendarRow.planned_for <= until,
        )
        if channel_id is not None:
            query = query.where(GrowthContentCalendarRow.channel_id == channel_id)
        rows = (
            await self._db.execute(query.order_by(GrowthContentCalendarRow.planned_for.asc()))
        ).scalars().all()
        return [_calendar_row_to_dict(row) for row in rows]

    async def replace_calendar_items(self, project_id: UUID, items: list[dict]) -> list[dict]:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthContentCalendarRow

        now = datetime.now(timezone.utc)
        existing = (
            await self._db.execute(
                select(GrowthContentCalendarRow).where(
                    GrowthContentCalendarRow.project_id == project_id,
                    GrowthContentCalendarRow.status == "planned",
                )
            )
        ).scalars().all()
        for row in existing:
            await self._db.delete(row)

        saved: list[dict] = []
        for item in items:
            planned_for = item.get("planned_for")
            planned_dt = None
            if planned_for:
                try:
                    planned_dt = datetime.fromisoformat(str(planned_for).replace("Z", "+00:00"))
                except ValueError:
                    planned_dt = None
            channel_id = item.get("channel_id")
            row = GrowthContentCalendarRow(
                id=uuid.uuid4(),
                project_id=project_id,
                channel_id=UUID(str(channel_id)) if channel_id else None,
                title=str(item.get("title") or "Conteúdo planejado")[:300],
                topic=str(item.get("topic") or "")[:500],
                planned_for=planned_dt,
                status=str(item.get("status") or "planned"),
                metadata_=dict(item.get("metadata") or {}),
                created_at=now,
            )
            self._db.add(row)
            saved.append(_calendar_row_to_dict(row))
        await self._db.flush()
        return saved

    async def create_calendar_items(self, project_id: UUID, items: list[dict]) -> list[dict]:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthContentCalendarRow

        now = datetime.now(timezone.utc)
        saved: list[dict] = []
        for item in items:
            planned_for = item.get("planned_for")
            planned_dt = None
            if planned_for:
                try:
                    planned_dt = datetime.fromisoformat(str(planned_for).replace("Z", "+00:00"))
                except ValueError:
                    planned_dt = None
            channel_id = item.get("channel_id")
            row = GrowthContentCalendarRow(
                id=uuid.uuid4(),
                project_id=project_id,
                channel_id=UUID(str(channel_id)) if channel_id else None,
                title=str(item.get("title") or "Conteudo planejado")[:300],
                topic=str(item.get("topic") or "")[:500],
                planned_for=planned_dt,
                status=str(item.get("status") or "planned"),
                metadata_=dict(item.get("metadata") or {}),
                created_at=now,
            )
            self._db.add(row)
            saved.append(_calendar_row_to_dict(row))
        await self._db.flush()
        return saved

    async def get_calendar_item(self, calendar_item_id: UUID) -> dict | None:
        from contentos_database.models import GrowthContentCalendarRow

        row = (
            await self._db.execute(
                select(GrowthContentCalendarRow).where(GrowthContentCalendarRow.id == calendar_item_id)
            )
        ).scalar_one_or_none()
        return _calendar_row_to_dict(row) if row else None

    async def list_planned_calendar_items(self, project_id: UUID, *, limit: int = 10) -> list[dict]:
        from contentos_database.models import GrowthContentCalendarRow

        rows = (
            await self._db.execute(
                select(GrowthContentCalendarRow)
                .where(
                    GrowthContentCalendarRow.project_id == project_id,
                    GrowthContentCalendarRow.status == "planned",
                )
                .order_by(GrowthContentCalendarRow.planned_for.asc().nullslast())
                .limit(limit)
            )
        ).scalars().all()
        return [_calendar_row_to_dict(row) for row in rows]

    async def mark_calendar_dispatched(
        self,
        calendar_item_id: UUID,
        *,
        pipeline_id: UUID,
        status: str = "dispatched",
    ) -> dict:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthContentCalendarRow

        row = (
            await self._db.execute(
                select(GrowthContentCalendarRow).where(GrowthContentCalendarRow.id == calendar_item_id)
            )
        ).scalar_one_or_none()
        if not row:
            raise ValueError("Calendar item not found")
        metadata = dict(row.metadata_ or {})
        metadata["pipeline_id"] = str(pipeline_id)
        metadata["dispatched_at"] = datetime.now(timezone.utc).isoformat()
        row.metadata_ = metadata
        row.status = status
        await self._db.flush()
        return _calendar_row_to_dict(row)

    async def mark_calendar_post_generated(
        self,
        calendar_item_id: UUID,
        *,
        artifacts: list[dict],
        formats: list[str],
        status: str | None = "post_ready",
        companion: bool = False,
    ) -> dict:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthContentCalendarRow

        row = (
            await self._db.execute(
                select(GrowthContentCalendarRow).where(GrowthContentCalendarRow.id == calendar_item_id)
            )
        ).scalar_one_or_none()
        if not row:
            raise ValueError("Calendar item not found")
        metadata = dict(row.metadata_ or {})
        now = datetime.now(timezone.utc).isoformat()
        if companion:
            metadata["companion_artifacts"] = artifacts
            metadata["companion_formats"] = formats
            metadata["companion_generated_at"] = now
        else:
            metadata["post_artifacts"] = artifacts
            metadata["post_formats"] = formats
            metadata["post_generated_at"] = now
            if status:
                row.status = status
        row.metadata_ = metadata
        await self._db.flush()
        return _calendar_row_to_dict(row)

    async def list_calendar_posts(self, project_id: UUID, *, limit: int = 50) -> list[dict]:
        from contentos_database.models import GrowthContentCalendarRow

        rows = (
            await self._db.execute(
                select(GrowthContentCalendarRow)
                .where(GrowthContentCalendarRow.project_id == project_id)
                .order_by(GrowthContentCalendarRow.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        posts: list[dict] = []
        for row in rows:
            item = _calendar_row_to_dict(row)
            metadata = item.get("metadata") or {}
            if metadata.get("post_artifacts") or metadata.get("companion_artifacts") or item.get("status") == "post_ready":
                posts.append(item)
        return posts

    async def mark_calendar_scheduled(
        self,
        calendar_item_id: UUID,
        *,
        schedule_id: UUID,
        mode: str,
        cron_expression: str,
        status: str = "pending_schedule",
    ) -> dict:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthContentCalendarRow

        row = (
            await self._db.execute(
                select(GrowthContentCalendarRow).where(GrowthContentCalendarRow.id == calendar_item_id)
            )
        ).scalar_one_or_none()
        if not row:
            raise ValueError("Calendar item not found")
        metadata = dict(row.metadata_ or {})
        metadata["schedule_id"] = str(schedule_id)
        metadata["scheduling_mode"] = mode
        metadata["cron_expression"] = cron_expression
        metadata["scheduled_at"] = datetime.now(timezone.utc).isoformat()
        row.metadata_ = metadata
        row.status = status
        await self._db.flush()
        return _calendar_row_to_dict(row)

    async def list_scheduled_calendar_items(self, project_id: UUID, *, limit: int = 50) -> list[dict]:
        from contentos_database.models import GrowthContentCalendarRow

        rows = (
            await self._db.execute(
                select(GrowthContentCalendarRow)
                .where(
                    GrowthContentCalendarRow.project_id == project_id,
                    GrowthContentCalendarRow.status.in_(["scheduled", "pending_schedule"]),
                )
                .order_by(GrowthContentCalendarRow.planned_for.asc().nullslast())
                .limit(limit)
            )
        ).scalars().all()
        return [_calendar_row_to_dict(row) for row in rows]

    async def save_project_report(
        self,
        *,
        project_id: UUID,
        score: float,
        summary: str,
        report: dict,
    ) -> None:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthReportRow

        now = datetime.now(timezone.utc)
        self._db.add(
            GrowthReportRow(
                id=uuid.uuid4(),
                project_id=project_id,
                channel_id=None,
                score=score,
                summary=summary,
                report=report,
                created_at=now,
            )
        )
        await self._db.flush()

    async def save_channel_manager_plan(self, channel_id: UUID, plan: dict) -> None:
        from datetime import datetime, timezone

        from contentos_database.models import GrowthChannelProfileRow

        row = (
            await self._db.execute(
                select(GrowthChannelProfileRow).where(GrowthChannelProfileRow.channel_id == channel_id)
            )
        ).scalar_one_or_none()
        if not row:
            return
        report = dict(row.report or {})
        report["channel_manager"] = plan
        row.report = report
        row.updated_at = datetime.now(timezone.utc)
        await self._db.flush()

    async def list_asset_performance(
        self,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
        limit: int = 20,
    ) -> list[dict]:
        from contentos_database.models import GrowthAssetPerformanceRow

        query = select(GrowthAssetPerformanceRow).where(GrowthAssetPerformanceRow.project_id == project_id)
        if channel_id is not None:
            query = query.where(GrowthAssetPerformanceRow.channel_id == channel_id)
        rows = (
            await self._db.execute(
                query.order_by(desc(GrowthAssetPerformanceRow.updated_at)).limit(min(limit, 100))
            )
        ).scalars().all()
        return [
            {
                "asset_id": str(row.asset_id) if row.asset_id else None,
                "project_id": str(row.project_id),
                "channel_id": str(row.channel_id) if row.channel_id else None,
                "uses": row.uses,
                "ctr": row.ctr,
                "retention_pct": row.retention_pct,
                "watch_time_seconds": row.watch_time_seconds,
                "engagement_rate": row.engagement_rate,
                "ai_score": row.ai_score,
                "metadata": dict(row.metadata_ or {}),
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]

    async def list_project_report_history(self, project_id: UUID, *, limit: int = 30) -> list[dict]:
        from contentos_database.models import GrowthReportRow

        rows = (
            await self._db.execute(
                select(GrowthReportRow)
                .where(GrowthReportRow.project_id == project_id)
                .order_by(desc(GrowthReportRow.created_at))
                .limit(min(limit, 100))
            )
        ).scalars().all()
        return [
            {
                "id": str(row.id),
                "project_id": str(row.project_id),
                "channel_id": str(row.channel_id) if row.channel_id else None,
                "score": row.score,
                "summary": row.summary,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]


def _calendar_row_to_dict(row) -> dict:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "channel_id": str(row.channel_id) if row.channel_id else None,
        "title": row.title,
        "topic": row.topic,
        "planned_for": row.planned_for.isoformat() if row.planned_for else None,
        "status": row.status,
        "metadata": dict(row.metadata_ or {}),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _competitor_from_row(row) -> CompetitorProfile:
    return CompetitorProfile(
        id=str(row.id),
        project_id=str(row.project_id),
        platform=row.platform,
        handle=row.handle,
        display_name=row.display_name,
        url=row.url,
        notes=row.notes or "",
        metrics=dict(row.metrics or {}),
        created_at=row.created_at.isoformat() if row.created_at else None,
    )
