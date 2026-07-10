"""Growth application service."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from contentos_growth.application.autonomous_calendar import (
    AutonomousCalendarPlan,
    build_autonomous_calendar_plan,
)
from contentos_growth.application.autonomous_execution import (
    AutonomousExecutionPlan,
    build_autonomous_execution_plan,
)
from contentos_growth.application.autopilot import GrowthAutopilotStatus, build_growth_autopilot_status
from contentos_growth.application.channel_analyzer import ChannelAnalysisResult, analyze_channel_snapshot
from contentos_growth.application.channel_intelligence import (
    ChannelIntelligenceSnapshot,
    build_channel_intelligence_snapshot,
)
from contentos_growth.application.channel_manager import (
    ChannelDailyPlan,
    ChannelManagerSignals,
    build_channel_daily_plan,
    enrich_channel_manager_actions,
    filter_calendar_for_channel,
    filter_competitors_for_platform,
    filter_performance_for_platform,
    recommendations_to_dicts,
)
from contentos_growth.application.channel_memory_service import ChannelMemoryService
from contentos_growth.application.closed_loop import ClosedLoopReport, build_closed_loop_report
from contentos_growth.application.competitor_analyzer import CompetitorAnalysisResult, analyze_competitor_snapshot
from contentos_growth.application.competitor_fetcher import fetch_competitor_data
from contentos_growth.application.content_factory_bridge import GrowthPipelineDispatch, prepare_calendar_dispatch
from contentos_growth.application.content_strategist import ContentStrategyPlan, generate_content_strategy_plan
from contentos_growth.application.growth_hardening import (
    GrowthHealthReport,
    OAuthChannelAudit,
    audit_channel_oauth,
    build_growth_health,
)
from contentos_growth.application.growth_history_builder import GrowthHistoryEvent, build_growth_history
from contentos_growth.application.growth_readiness import build_growth_readiness
from contentos_growth.application.growth_report_builder import assemble_growth_report, gather_growth_report_signals
from contentos_growth.application.multi_channel_scope import (
    ChannelOverviewItem,
    ChannelScope,
    ChannelWorkspace,
    build_channel_overview_item,
    build_workspace_summary,
    filter_learning_for_platform,
    filter_recommendations_for_channel,
    infer_channel_health,
)
from contentos_growth.application.performance_learning_interpreter import (
    PerformanceInterpretation,
    interpret_performance_insights,
)
from contentos_growth.application.platform_overview import get_channel_overview
from contentos_growth.application.post_manager import (
    PostGenerationPlan,
    PostGenerationResult,
    generate_post_report,
    plan_calendar_post,
)
from contentos_growth.application.repository import GrowthRepository
from contentos_growth.application.smart_scheduler_bridge import (
    GrowthSchedulePlan,
    build_growth_schedule_plan,
    compute_schedule_next_run,
    normalize_scheduling_mode,
)
from contentos_growth.domain import CompetitorProfile, GrowthRecommendation, GrowthReport, GrowthStrategy


class GrowthService:
    def __init__(self, repository: GrowthRepository, channel_memory: ChannelMemoryService | None = None) -> None:
        self._repo = repository
        self._channel_memory = channel_memory or ChannelMemoryService()

    async def list_channels(self, project_id: UUID):
        return await self._repo.list_channel_profiles(project_id)

    async def get_channel_profile(self, channel_id: UUID):
        return await self._repo.get_channel_profile(channel_id)

    async def analyze_channel(
        self,
        *,
        db: AsyncSession,
        channel_id: UUID,
        project_id: UUID,
        platform: str,
        channel_name: str,
        overview: dict | None,
    ) -> ChannelAnalysisResult:
        result = analyze_channel_snapshot(
            channel_id=str(channel_id),
            project_id=str(project_id),
            platform=platform,
            channel_name=channel_name,
            overview=overview,
        )
        await self._repo.save_channel_analysis(
            project_id=project_id,
            channel_id=channel_id,
            score=result.score,
            profile_data=result.profile,
            report={**result.report, "summary": result.summary},
            recommendations=result.recommendations,
            summary=result.summary,
        )
        await self._channel_memory.seed_from_analysis(
            db,
            channel_id=channel_id,
            project_id=project_id,
            analysis=result,
            overview=overview,
        )
        return result

    async def list_channel_analysis_history(self, channel_id: UUID, *, limit: int = 20) -> list[dict]:
        return await self._repo.list_channel_analysis_history(channel_id, limit=limit)

    async def list_competitors(self, project_id: UUID) -> list[CompetitorProfile]:
        return await self._repo.list_competitors(project_id)

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
        return await self._repo.create_competitor(
            project_id,
            platform=platform.lower().strip(),
            handle=handle.strip(),
            display_name=display_name.strip() or handle.strip(),
            url=url,
            notes=notes,
        )

    async def get_competitor(self, competitor_id: UUID) -> CompetitorProfile | None:
        return await self._repo.get_competitor(competitor_id)

    async def sync_competitor(self, competitor_id: UUID, *, limit: int = 10) -> CompetitorProfile:
        competitor = await self._repo.get_competitor(competitor_id)
        if not competitor:
            raise ValueError("Competitor not found")
        fetched = await fetch_competitor_data(competitor.platform, competitor.handle, limit=limit)
        merged = {**(competitor.metrics or {}), **fetched}
        display_name = fetched.get("channel_totals", {}).get("title") or competitor.display_name
        channel_id = fetched.get("channel_totals", {}).get("youtube_channel_id")
        url = competitor.url
        if not url and channel_id:
            url = f"https://www.youtube.com/channel/{channel_id}"
        return await self._repo.update_competitor(
            competitor_id,
            metrics=merged,
            display_name=display_name,
            url=url,
        )

    async def analyze_competitor(self, competitor_id: UUID) -> CompetitorAnalysisResult:
        competitor = await self._repo.get_competitor(competitor_id)
        if not competitor:
            raise ValueError("Competitor not found")
        result = analyze_competitor_snapshot(
            competitor_id=str(competitor_id),
            project_id=competitor.project_id,
            platform=competitor.platform,
            handle=competitor.handle,
            display_name=competitor.display_name,
            metrics=competitor.metrics or {},
        )
        merged = {
            **(competitor.metrics or {}),
            "analysis": result.to_dict(),
            "patterns": result.patterns,
            "last_analyzed_at": result.analyzed_at,
        }
        await self._repo.update_competitor(competitor_id, metrics=merged)
        if result.recommendations:
            await self._repo.save_competitor_recommendations(
                project_id=UUID(competitor.project_id),
                competitor_id=competitor_id,
                recommendations=result.recommendations,
            )
        return result

    async def sync_project_competitors(self, project_id: UUID, *, limit: int = 10) -> list[dict]:
        competitors = await self._repo.list_competitors(project_id)
        results: list[dict] = []
        for competitor in competitors:
            if not competitor.id:
                continue
            competitor_id = UUID(competitor.id)
            try:
                updated = await self.sync_competitor(competitor_id, limit=limit)
                results.append(
                    {
                        "competitor_id": competitor.id,
                        "handle": updated.handle,
                        "synced": not (updated.metrics or {}).get("sync_error"),
                        "error": (updated.metrics or {}).get("sync_error"),
                    }
                )
            except ValueError as exc:
                results.append(
                    {
                        "competitor_id": competitor.id,
                        "handle": competitor.handle,
                        "synced": False,
                        "error": str(exc),
                    }
                )
        return results

    async def list_recommendations(
        self,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
    ) -> list[GrowthRecommendation]:
        recs = await self._repo.list_recommendations(project_id, channel_id=channel_id)
        if channel_id is not None:
            return filter_recommendations_for_channel(recs, str(channel_id))
        if recs:
            return recs
        channels = await self._repo.list_channel_profiles(project_id)
        if not channels:
            return [
                GrowthRecommendation(
                    id=None,
                    project_id=str(project_id),
                    channel_id=None,
                    kind="channel",
                    title="Conectar primeiro canal",
                    detail="Cadastre ou conecte um canal para iniciar a inteligencia de crescimento.",
                    priority="high",
                    source="growth_foundation",
                )
            ]
        return [
            GrowthRecommendation(
                id=None,
                project_id=str(project_id),
                channel_id=None,
                kind="competitor",
                title="Cadastrar concorrentes de referencia",
                detail="Adicione 3 a 5 concorrentes para comparar frequencia, formato e oportunidades.",
                priority="medium",
                source="growth_foundation",
            )
        ]

    async def save_recommendations(self, project_id: UUID, recommendations: list[GrowthRecommendation]) -> int:
        return await self._repo.save_recommendations(project_id, recommendations)

    async def get_strategy(
        self,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
    ) -> GrowthStrategy:
        strategy = await self._repo.get_strategy(project_id, channel_id=channel_id)
        if strategy:
            return strategy
        return GrowthStrategy(
            project_id=str(project_id),
            positioning="Validar crescimento com canais conectados",
            goals=["Validar crescimento com canais conectados"],
            kpis={"baseline": "views, engagement, retention"},
            cadence={"weekly_posts": 3, "review_cycle": "weekly"},
        )

    async def get_content_calendar(
        self,
        project_id: UUID,
        *,
        horizon_days: int = 30,
        channel_id: UUID | None = None,
    ) -> list[dict]:
        return await self._repo.list_calendar_items(
            project_id,
            horizon_days=horizon_days,
            channel_id=channel_id,
        )

    async def generate_content_strategy(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        horizon_days: int = 30,
    ) -> ContentStrategyPlan:
        channels = await self._repo.list_channel_profiles(project_id)
        recommendations = await self._repo.list_recommendations(project_id)
        if not recommendations:
            recommendations = await self.list_recommendations(project_id)
        base_strategy = await self.get_strategy(project_id)
        signals = await gather_growth_report_signals(db, project_id)

        positioning = (
            signals.memory_mission
            or signals.memory_niche
            or (base_strategy.positioning if base_strategy else "")
            or "Crescimento orgânico com conteúdo consistente"
        )

        channel_memory_by_channel: dict[str, dict[str, Any]] = {}
        for channel in channels:
            memory = await self._channel_memory.get_async(db, UUID(channel.channel_id))
            if memory:
                channel_memory_by_channel[channel.channel_id] = memory.to_dict()

        posting_gap = None
        for ch in channels:
            gap = (ch.profile or {}).get("posting_gap_days")
            if gap is not None:
                posting_gap = float(gap)
                break

        opportunities: list[str] = []
        report = assemble_growth_report(
            project_id=project_id,
            channels=channels,
            competitors=await self._repo.list_competitors(project_id),
            stored_recommendations=recommendations,
            base_strategy=base_strategy,
            signals=signals,
        )
        opportunities = list(report.opportunities)

        plan = generate_content_strategy_plan(
            project_id=str(project_id),
            channels=channels,
            recommendations=recommendations,
            positioning=positioning,
            opportunities=opportunities,
            channel_memory_by_channel=channel_memory_by_channel,
            posting_gap_days=posting_gap,
            horizon_days=horizon_days,
            base_strategy=base_strategy,
        )
        saved_strategy = await self._repo.save_strategy(project_id, plan.strategy, status="active")
        from dataclasses import replace

        await self._repo.replace_calendar_items(project_id, plan.calendar.items)
        return replace(plan, strategy=saved_strategy)

    async def build_autonomous_calendar_plan(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
        horizon_days: int = 30,
        max_items: int = 20,
        mode: str = "draft",
    ) -> AutonomousCalendarPlan:
        channels = await self._repo.list_channel_profiles(project_id)
        if channel_id is not None:
            channels = [channel for channel in channels if channel.channel_id == str(channel_id)]
            if not channels:
                raise ValueError("Channel not found")

        snapshots: list[ChannelIntelligenceSnapshot] = []
        for channel in channels:
            try:
                snapshots.append(await self.build_channel_intelligence_snapshot(db, UUID(channel.channel_id)))
            except Exception:
                continue

        existing_calendar = await self._repo.list_calendar_items(
            project_id,
            horizon_days=horizon_days,
            channel_id=channel_id,
        )
        strategy = await self.get_strategy(project_id, channel_id=channel_id)
        return build_autonomous_calendar_plan(
            project_id=str(project_id),
            snapshots=snapshots,
            existing_calendar=existing_calendar,
            strategy=strategy,
            horizon_days=horizon_days,
            mode=mode,
            max_items=max_items,
        )

    async def apply_autonomous_calendar_plan(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
        horizon_days: int = 30,
        max_items: int = 20,
        mode: str = "assisted",
    ) -> tuple[AutonomousCalendarPlan, list[dict]]:
        plan = await self.build_autonomous_calendar_plan(
            db,
            project_id,
            channel_id=channel_id,
            horizon_days=horizon_days,
            max_items=max_items,
            mode=mode,
        )
        items = plan.to_calendar_items()
        saved = await self._repo.create_calendar_items(project_id, items) if items else []
        return plan, saved

    async def prepare_calendar_dispatch(
        self,
        calendar_item_id: UUID,
        *,
        workflow_name: str | None = None,
    ) -> GrowthPipelineDispatch:
        item = await self._repo.get_calendar_item(calendar_item_id)
        if not item:
            raise ValueError("Calendar item not found")
        if item.get("status") not in ("planned",):
            raise ValueError(f"Calendar item cannot be dispatched from status {item.get('status')}")
        strategy = await self.get_strategy(UUID(item["project_id"]))
        return prepare_calendar_dispatch(calendar_item=item, strategy=strategy, workflow_name=workflow_name)

    async def list_planned_calendar_items(self, project_id: UUID, *, limit: int = 10) -> list[dict]:
        return await self._repo.list_planned_calendar_items(project_id, limit=limit)

    async def mark_calendar_dispatched(
        self,
        calendar_item_id: UUID,
        *,
        pipeline_id: UUID,
        status: str = "dispatched",
    ) -> dict:
        return await self._repo.mark_calendar_dispatched(
            calendar_item_id,
            pipeline_id=pipeline_id,
            status=status,
        )

    async def prepare_calendar_post(
        self,
        calendar_item_id: UUID,
        *,
        include_companion: bool = False,
    ) -> PostGenerationPlan:
        item = await self._repo.get_calendar_item(calendar_item_id)
        if not item:
            raise ValueError("Calendar item not found")
        if item.get("status") not in ("planned", "post_ready"):
            raise ValueError(f"Calendar item cannot generate post from status {item.get('status')}")
        strategy = await self.get_strategy(UUID(item["project_id"]))
        plan = plan_calendar_post(calendar_item=item, strategy=strategy, include_companion=include_companion)
        if not plan.text_formats and plan.mode == "text":
            raise ValueError(f"No text formats for platform {plan.platform}")
        return plan

    async def generate_calendar_post(
        self,
        calendar_item_id: UUID,
        *,
        include_companion: bool = False,
        formats: list[str] | None = None,
        companion: bool = False,
    ) -> PostGenerationResult:
        plan = await self.prepare_calendar_post(calendar_item_id, include_companion=include_companion or companion)
        result = generate_post_report(plan=plan, formats=formats)
        await self._repo.mark_calendar_post_generated(
            calendar_item_id,
            artifacts=result.artifacts,
            formats=result.formats,
            companion=companion,
        )
        return result

    async def list_calendar_posts(self, project_id: UUID, *, limit: int = 50) -> list[dict]:
        return await self._repo.list_calendar_posts(project_id, limit=limit)

    async def get_calendar_item(self, calendar_item_id: UUID) -> dict | None:
        return await self._repo.get_calendar_item(calendar_item_id)

    async def schedule_calendar_item(
        self,
        db: AsyncSession,
        calendar_item_id: UUID,
        *,
        user_id: UUID,
        org_id: UUID | None,
        mode: str = "assisted",
        timezone: str = "UTC",
        workflow_name: str | None = None,
    ) -> tuple[GrowthSchedulePlan, dict]:
        from contentos_database.cron_helpers import validate_cron
        from contentos_database.models import PipelineSchedule

        item = await self._repo.get_calendar_item(calendar_item_id)
        if not item:
            raise ValueError("Calendar item not found")
        strategy = await self.get_strategy(UUID(item["project_id"]))
        scheduling_mode = normalize_scheduling_mode(mode)
        plan = build_growth_schedule_plan(
            calendar_item=item,
            strategy=strategy,
            mode=scheduling_mode,
            timezone=timezone,
            workflow_name=workflow_name,
        )
        cron = validate_cron(plan.cron_expression)
        next_run = compute_schedule_next_run(cron, plan.timezone)
        row = PipelineSchedule(
            project_id=UUID(plan.project_id),
            org_id=org_id,
            name=plan.name,
            topic=plan.topic,
            workflow_name=plan.workflow_name,
            cron_expression=cron,
            timezone=plan.timezone,
            is_active=plan.is_active,
            created_by_user_id=user_id,
            next_run_at=next_run,
            context_json=plan.context_json,
        )
        db.add(row)
        await db.flush()
        calendar_status = "scheduled" if scheduling_mode == "automatic" else "pending_schedule"
        updated = await self._repo.mark_calendar_scheduled(
            calendar_item_id,
            schedule_id=row.id,
            mode=scheduling_mode,
            cron_expression=cron,
            status=calendar_status,
        )
        schedule_dict = {
            "id": str(row.id),
            "project_id": str(row.project_id),
            "name": row.name,
            "topic": row.topic,
            "cron_expression": row.cron_expression,
            "timezone": row.timezone,
            "is_active": row.is_active,
            "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        }
        return plan, {**schedule_dict, "calendar_item": updated}

    async def approve_calendar_schedule(
        self,
        db: AsyncSession,
        calendar_item_id: UUID,
    ) -> dict:
        from contentos_database.models import PipelineSchedule

        item = await self._repo.get_calendar_item(calendar_item_id)
        if not item:
            raise ValueError("Calendar item not found")
        metadata = item.get("metadata") or {}
        schedule_id = metadata.get("schedule_id")
        if not schedule_id:
            raise ValueError("Calendar item has no pending schedule")
        row = await db.get(PipelineSchedule, UUID(str(schedule_id)))
        if not row:
            raise ValueError("Pipeline schedule not found")
        row.is_active = True
        await db.flush()
        updated = await self._repo.mark_calendar_scheduled(
            calendar_item_id,
            schedule_id=row.id,
            mode=str(metadata.get("scheduling_mode") or "assisted"),
            cron_expression=str(metadata.get("cron_expression") or row.cron_expression),
            status="scheduled",
        )
        return updated

    async def list_scheduled_calendar_items(self, project_id: UUID, *, limit: int = 50) -> list[dict]:
        return await self._repo.list_scheduled_calendar_items(project_id, limit=limit)

    async def sync_calendar_schedules(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        user_id: UUID,
        org_id: UUID | None,
        mode: str = "assisted",
        timezone: str = "UTC",
        limit: int = 10,
    ) -> list[dict]:
        planned = await self._repo.list_planned_calendar_items(project_id, limit=limit)
        created: list[dict] = []
        for item in planned:
            item_id = item.get("id")
            if not item_id:
                continue
            try:
                _, result = await self.schedule_calendar_item(
                    db,
                    UUID(item_id),
                    user_id=user_id,
                    org_id=org_id,
                    mode=mode,
                    timezone=timezone,
                )
                created.append(result)
            except ValueError:
                continue
        return created

    async def interpret_performance(self, db: AsyncSession, project_id: UUID) -> PerformanceInterpretation:
        from contentos_intelligence.application.performance_learning import list_performance_insights

        rows = await list_performance_insights(db, project_id, limit=50)
        return interpret_performance_insights(str(project_id), rows)

    async def sync_performance_learning(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        persist: bool = True,
        index_kb: bool | None = None,
        save_recommendations: bool = True,
    ) -> PerformanceInterpretation:
        from contentos_intelligence.application.performance_learning import (
            performance_learning_enabled,
            process_project_performance_learning,
        )

        if performance_learning_enabled():
            await process_project_performance_learning(
                db,
                project_id,
                persist=persist,
                index_kb=index_kb,
            )
        interpretation = await self.interpret_performance(db, project_id)
        if save_recommendations and interpretation.recommendations:
            await self._repo.save_recommendations(project_id, interpretation.recommendations)
        return interpretation

    async def build_closed_loop_report(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        sync_performance: bool = False,
        save_recommendations: bool = True,
        mode: str = "assisted",
        horizon_days: int = 7,
        max_actions: int = 5,
        timezone: str = "UTC",
        workflow_name: str | None = None,
        persist_report: bool = True,
    ) -> ClosedLoopReport:
        saved_count = 0
        if sync_performance:
            before = len(await self._repo.list_recommendations(project_id))
            performance = await self.sync_performance_learning(
                db,
                project_id,
                persist=True,
                save_recommendations=save_recommendations,
            )
            after = len(await self._repo.list_recommendations(project_id))
            saved_count = max(0, after - before)
        else:
            performance = await self.interpret_performance(db, project_id)

        growth_report = await self.build_report(db, project_id, persist=persist_report)
        execution_plan = await self.build_autonomous_execution_plan(
            db,
            project_id,
            mode=mode,
            horizon_days=horizon_days,
            max_actions=max_actions,
            timezone=timezone,
            workflow_name=workflow_name,
        )
        return build_closed_loop_report(
            project_id=str(project_id),
            growth_report=growth_report,
            performance=performance,
            execution_plan=execution_plan,
            saved_recommendations=saved_count,
        )

    async def gather_channel_manager_signals(
        self,
        db: AsyncSession,
        channel_id: UUID,
    ) -> ChannelManagerSignals:
        profile = await self._repo.get_channel_profile(channel_id)
        if not profile:
            raise ValueError("Channel not found")

        project_id = UUID(profile.project_id)
        platform = profile.platform
        memory_data = await self._channel_memory.get_async(db, channel_id)
        channel_memory = memory_data.to_dict() if memory_data else {}

        overview = await get_channel_overview(db, channel_id, platform=platform) or {}

        perf_rows: list[dict[str, Any]] = []
        try:
            from contentos_intelligence.application.performance_learning import list_performance_insights

            all_perf = await list_performance_insights(db, project_id, limit=50)
            perf_rows = filter_performance_for_platform(all_perf, platform)
        except Exception:
            pass

        competitors = filter_competitors_for_platform(
            await self._repo.list_competitors(project_id),
            platform,
        )

        calendar_all = await self._repo.list_calendar_items(project_id, horizon_days=30)
        calendar_items = filter_calendar_for_channel(calendar_all, str(channel_id))

        recommendations = recommendations_to_dicts(await self._repo.list_recommendations(project_id))

        trend_brief: dict[str, Any] = {}
        try:
            from contentos_shared.trend_intelligence import build_trend_brief

            trend_brief = build_trend_brief(
                topic=profile.name or platform,
                niche=str(channel_memory.get("niche") or ""),
                insights=perf_rows[:10],
            )
        except Exception:
            pass

        asset_count = 0
        try:
            from contentos_growth.application.growth_report_builder import gather_growth_report_signals

            signals = await gather_growth_report_signals(db, project_id)
            asset_count = signals.asset_count
        except Exception:
            pass

        posting_gap = (profile.profile or {}).get("posting_gap_days")
        if posting_gap is None and overview:
            posting_gap = overview.get("posting_gap_days")

        return ChannelManagerSignals(
            channel_id=str(channel_id),
            project_id=str(project_id),
            platform=platform,
            channel_name=profile.name,
            channel_score=float(profile.score or 0),
            has_credentials=profile.has_credentials,
            overview=overview,
            channel_memory=channel_memory,
            performance_rows=perf_rows,
            competitors=competitors,
            calendar_items=calendar_items,
            recommendations=recommendations,
            trend_brief=trend_brief,
            posting_gap_days=float(posting_gap) if posting_gap is not None else None,
            asset_count=asset_count,
        )

    async def build_channel_manager_plan(
        self,
        db: AsyncSession,
        channel_id: UUID,
        *,
        scheduling_mode: str = "assisted",
        timezone: str = "UTC",
        horizon_days: int = 7,
        workflow_name: str | None = None,
        persist: bool = True,
    ) -> ChannelDailyPlan:
        signals = await self.gather_channel_manager_signals(db, channel_id)
        strategy = await self.get_strategy(UUID(signals.project_id))
        plan = build_channel_daily_plan(
            signals,
            strategy=strategy,
            scheduling_mode=scheduling_mode,
            horizon_days=horizon_days,
        )

        calendar_by_id: dict[str, dict[str, Any]] = {
            str(item.get("id")): item for item in signals.calendar_items if item.get("id")
        }
        enriched = enrich_channel_manager_actions(
            plan,
            calendar_by_id=calendar_by_id,
            strategy=strategy,
            scheduling_mode=scheduling_mode,
            timezone=timezone,
            workflow_name=workflow_name,
        )

        if persist:
            await self._repo.save_channel_manager_plan(channel_id, enriched.to_dict())
        return enriched

    async def get_channel_workspace(
        self,
        db: AsyncSession,
        channel_id: UUID,
        *,
        org_id: UUID | None = None,
        horizon_days: int = 30,
    ) -> ChannelWorkspace:
        profile = await self._repo.get_channel_profile(channel_id)
        if not profile:
            raise ValueError("Channel not found")

        project_id = UUID(profile.project_id)
        memory_data = await self._channel_memory.get_async(db, channel_id)
        memory = memory_data.to_dict() if memory_data else {}

        overview = await get_channel_overview(db, channel_id, platform=profile.platform) or {}

        perf_rows: list[dict[str, Any]] = []
        learning_rows: list[dict[str, Any]] = []
        try:
            from contentos_intelligence.application.performance_learning import list_performance_insights

            all_perf = await list_performance_insights(db, project_id, limit=50)
            perf_rows = filter_performance_for_platform(all_perf, profile.platform)
        except Exception:
            pass

        try:
            from contentos_intelligence.infrastructure.learning_repository import LearningRepository

            all_learning = await LearningRepository().list_by_project(db, project_id, limit=30)
            learning_rows = filter_learning_for_platform(all_learning, profile.platform)
        except Exception:
            pass

        calendar = await self._repo.list_calendar_items(
            project_id,
            horizon_days=horizon_days,
            channel_id=channel_id,
        )
        strategy = await self.get_strategy(project_id, channel_id=channel_id)
        recommendations = await self.list_recommendations(project_id, channel_id=channel_id)
        competitors = filter_competitors_for_platform(
            await self._repo.list_competitors(project_id),
            profile.platform,
        )
        assets = await self._repo.list_asset_performance(project_id, channel_id=channel_id, limit=20)

        manager_plan = None
        if profile.report:
            manager_plan = (profile.report or {}).get("channel_manager")

        scope = ChannelScope(
            org_id=str(org_id) if org_id else None,
            project_id=str(project_id),
            channel_id=str(channel_id),
            platform=profile.platform,
            channel_name=profile.name,
        )
        health = infer_channel_health(profile=profile, calendar=calendar, performance=perf_rows)

        return ChannelWorkspace(
            scope=scope,
            profile=profile,
            memory=memory,
            analytics=overview,
            performance=perf_rows,
            learning=learning_rows,
            calendar=calendar,
            strategy=strategy,
            recommendations=recommendations,
            competitors=competitors,
            assets=assets,
            manager_plan=manager_plan,
            health_status=health,
            summary=build_workspace_summary(scope, health, calendar),
        )

    async def build_channel_intelligence_snapshot(
        self,
        db: AsyncSession,
        channel_id: UUID,
    ) -> ChannelIntelligenceSnapshot:
        profile = await self._repo.get_channel_profile(channel_id)
        if not profile:
            raise ValueError("Channel not found")

        project_id = UUID(profile.project_id)
        brand: dict[str, Any] = {}
        try:
            from contentos_memory import get_memory_service

            memory_data = await get_memory_service().get_async(db, project_id)
            brand = memory_data.to_brand_dict() if memory_data else {}
        except Exception:
            brand = {}

        channel_memory_data = await self._channel_memory.get_async(db, channel_id)
        channel_memory = channel_memory_data.to_dict() if channel_memory_data else {}

        performance_rows: list[dict[str, Any]] = []
        try:
            from contentos_intelligence.application.performance_learning import list_performance_insights

            all_perf = await list_performance_insights(db, project_id, limit=100)
            performance_rows = filter_performance_for_platform(all_perf, profile.platform)
        except Exception:
            performance_rows = []

        competitors = filter_competitors_for_platform(
            await self._repo.list_competitors(project_id),
            profile.platform,
        )
        strategy = await self.get_strategy(project_id, channel_id=channel_id)
        if strategy is None:
            strategy = await self.get_strategy(project_id)
        recommendations = await self._repo.list_recommendations(project_id, channel_id=channel_id)

        return build_channel_intelligence_snapshot(
            channel=profile,
            brand=brand,
            channel_memory=channel_memory,
            performance_rows=performance_rows,
            competitors=competitors,
            strategy=strategy,
            recommendations=recommendations,
        )

    async def list_project_channels_overview(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        horizon_days: int = 30,
    ) -> list[ChannelOverviewItem]:
        channels = await self._repo.list_channel_profiles(project_id)
        all_calendar = await self._repo.list_calendar_items(project_id, horizon_days=horizon_days)
        all_recommendations = await self._repo.list_recommendations(project_id)

        perf_by_platform: dict[str, list[dict[str, Any]]] = {}
        try:
            from contentos_intelligence.application.performance_learning import list_performance_insights

            all_perf = await list_performance_insights(db, project_id, limit=100)
            for row in all_perf:
                platform = str(row.get("platform") or "unknown")
                perf_by_platform.setdefault(platform, []).append(row)
        except Exception:
            pass

        overview_items: list[ChannelOverviewItem] = []
        for channel in channels:
            calendar = filter_calendar_for_channel(all_calendar, channel.channel_id)
            recommendations = filter_recommendations_for_channel(all_recommendations, channel.channel_id)
            performance = perf_by_platform.get(channel.platform, [])
            overview_items.append(
                build_channel_overview_item(
                    channel,
                    calendar=calendar,
                    recommendations=recommendations,
                    performance=performance,
                )
            )
        return overview_items

    async def build_autopilot_status(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        mode: str = "assisted",
        horizon_days: int = 30,
        timezone: str = "UTC",
        workflow_name: str | None = None,
    ) -> GrowthAutopilotStatus:
        channels = await self._repo.list_channel_profiles(project_id)
        calendar = await self._repo.list_calendar_items(project_id, horizon_days=horizon_days)
        recommendations = await self._repo.list_recommendations(project_id)
        strategy = await self.get_strategy(project_id)

        plans: dict[str, ChannelDailyPlan] = {}
        for channel in channels:
            try:
                plan = await self.build_channel_manager_plan(
                    db,
                    UUID(channel.channel_id),
                    scheduling_mode=mode,
                    timezone=timezone,
                    horizon_days=min(horizon_days, 30),
                    workflow_name=workflow_name,
                    persist=False,
                )
                plans[channel.channel_id] = plan
            except Exception:
                continue

        return build_growth_autopilot_status(
            project_id=str(project_id),
            channels=channels,
            calendar_items=calendar,
            recommendations=recommendations,
            strategy=strategy,
            channel_plans=plans,
            readiness=build_growth_readiness().to_dict(),
            mode=mode,
        )

    async def build_autonomous_execution_plan(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        mode: str = "assisted",
        horizon_days: int = 7,
        max_actions: int = 5,
        timezone: str = "UTC",
        workflow_name: str | None = None,
    ) -> AutonomousExecutionPlan:
        channels = await self._repo.list_channel_profiles(project_id)
        channel_plans: list[ChannelDailyPlan] = []
        for channel in channels:
            try:
                plan = await self.build_channel_manager_plan(
                    db,
                    UUID(channel.channel_id),
                    scheduling_mode=mode,
                    timezone=timezone,
                    horizon_days=horizon_days,
                    workflow_name=workflow_name,
                    persist=False,
                )
                channel_plans.append(plan)
            except Exception:
                continue
        return build_autonomous_execution_plan(
            project_id=str(project_id),
            channel_plans=channel_plans,
            mode=mode,
            max_actions=max_actions,
        )

    async def audit_project_oauth(self, db: AsyncSession, project_id: UUID) -> list[OAuthChannelAudit]:
        from contentos_database.models import Channel
        from sqlalchemy import select

        rows = (
            await db.execute(
                select(Channel).where(Channel.project_id == project_id).order_by(Channel.created_at.desc())
            )
        ).scalars().all()
        return [
            audit_channel_oauth(
                channel_id=str(channel.id),
                project_id=str(channel.project_id),
                platform=channel.platform,
                channel_name=channel.name,
                credentials=dict(channel.credentials or {}),
            )
            for channel in rows
        ]

    async def get_growth_health(
        self,
        db: AsyncSession,
        project_id: UUID | None = None,
        *,
        external_checks: dict[str, bool] | None = None,
    ) -> GrowthHealthReport:
        checks: dict[str, bool] = {"database": True, "growth_package": True}
        if external_checks:
            checks.update(external_checks)

        try:
            from sqlalchemy import text

            await db.execute(text("SELECT 1"))
        except Exception:
            checks["database"] = False

        oauth_audits: list[OAuthChannelAudit] = []
        if project_id is not None:
            try:
                oauth_audits = await self.audit_project_oauth(db, project_id)
                checks["oauth_audit"] = all(row.status == "ok" for row in oauth_audits) if oauth_audits else True
            except Exception:
                checks["oauth_audit"] = False

        return build_growth_health(checks=checks, oauth_audits=oauth_audits)

    async def list_growth_history(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        limit: int = 50,
    ) -> list[GrowthHistoryEvent]:
        channels = await self._repo.list_channel_profiles(project_id)
        calendar = await self._repo.list_calendar_items(project_id, horizon_days=90)
        posts = await self._repo.list_calendar_posts(project_id, limit=limit)
        schedules_raw = await self._repo.list_scheduled_calendar_items(project_id, limit=limit)
        reports = await self._repo.list_project_report_history(project_id, limit=20)

        schedules: list[dict[str, Any]] = []
        for item in schedules_raw:
            metadata = item.get("metadata") or {}
            schedules.append(
                {
                    "id": metadata.get("schedule_id"),
                    "name": item.get("title"),
                    "topic": item.get("topic"),
                    "cron_expression": metadata.get("cron_expression"),
                    "is_active": item.get("status") == "scheduled",
                    "next_run_at": item.get("planned_for"),
                    "calendar_item_id": item.get("id"),
                }
            )

        return build_growth_history(
            project_id=str(project_id),
            calendar_items=calendar,
            posts=posts,
            schedules=schedules,
            channels=channels,
            reports=reports,
        )[:limit]

    async def build_report(self, db: AsyncSession, project_id: UUID, *, persist: bool = True) -> GrowthReport:
        channels = await self._repo.list_channel_profiles(project_id)
        competitors = await self._repo.list_competitors(project_id)
        stored_recommendations = await self._repo.list_recommendations(project_id)
        base_strategy = await self.get_strategy(project_id)
        signals = await gather_growth_report_signals(db, project_id)
        report = assemble_growth_report(
            project_id=project_id,
            channels=channels,
            competitors=competitors,
            stored_recommendations=stored_recommendations,
            base_strategy=base_strategy,
            signals=signals,
        )
        if persist:
            await self._repo.save_project_report(
                project_id=project_id,
                score=report.score,
                summary=report.summary,
                report=report.to_dict(),
            )
        return report
