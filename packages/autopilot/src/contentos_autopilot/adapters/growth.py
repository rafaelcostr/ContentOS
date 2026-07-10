"""Growth adapter for the Autopilot brain."""

from __future__ import annotations

from uuid import UUID

from contentos_autopilot.domain import (
    AutopilotAction,
    AutopilotContext,
    AutopilotMode,
    AutopilotSignal,
)
from contentos_autopilot.market import MarketIntelligenceReport, build_market_intelligence_report
from contentos_autopilot.objectives import build_objective_tree
from contentos_autopilot.twin import ChannelTwinSnapshot, build_channel_twin_snapshot


class GrowthAutopilotContextProvider:
    """Convert existing Growth reports into pure Autopilot context."""

    def __init__(self, growth_service, db) -> None:
        self._growth_service = growth_service
        self._db = db

    async def build_context(
        self,
        project_id: str,
        *,
        mode: AutopilotMode = "assisted",
        horizon_days: int = 7,
        max_actions: int = 5,
    ) -> AutopilotContext:
        project_uuid = UUID(project_id)
        status_report = await self._growth_service.build_autopilot_status(
            self._db,
            project_uuid,
            mode=mode,
            horizon_days=max(horizon_days, 7),
        )
        execution_plan = await self._growth_service.build_autonomous_execution_plan(
            self._db,
            project_uuid,
            mode=mode,
            horizon_days=horizon_days,
            max_actions=max_actions,
        )
        closed_loop = await self._growth_service.build_closed_loop_report(
            self._db,
            project_uuid,
            sync_performance=False,
            mode=mode,
            horizon_days=horizon_days,
            max_actions=max_actions,
            persist_report=False,
        )

        status_data = status_report.to_dict()
        execution_data = execution_plan.to_dict()
        loop_data = closed_loop.to_dict()

        signals = [
            AutopilotSignal(
                source="growth_status",
                kind="status",
                title=status_data.get("summary") or "Growth status",
                detail=", ".join(status_data.get("next_actions") or []),
                priority="high" if status_data.get("status") == "blocked" else "medium",
                metadata={"score": status_data.get("score"), "status": status_data.get("status")},
            ),
            AutopilotSignal(
                source="closed_loop",
                kind="learning",
                title=loop_data.get("summary") or "Closed loop",
                detail=", ".join(loop_data.get("learned") or []),
                priority="high" if loop_data.get("status") == "blocked" else "medium",
                metadata={"score": loop_data.get("score"), "next_cycle": loop_data.get("next_cycle") or {}},
            ),
        ]

        actions = [
            AutopilotAction(
                action=str(action.get("action") or ""),
                title=str(action.get("title") or ""),
                detail=str(action.get("detail") or ""),
                priority=str(action.get("priority") or "medium"),
                delegate_to=str(action.get("delegate_to") or (action.get("execution") or {}).get("type") or "growth"),
                can_delegate=bool(action.get("can_execute")),
                block_reason=action.get("block_reason"),
                metadata={
                    "channel_id": action.get("channel_id"),
                    "calendar_item_id": action.get("calendar_item_id"),
                    "platform": action.get("platform"),
                },
            )
            for action in execution_data.get("actions") or []
        ]

        blockers = [
            *list(status_data.get("blockers") or []),
            *list(loop_data.get("blockers") or []),
        ]

        return AutopilotContext(
            project_id=project_id,
            mode=mode,
            status=str(status_data.get("status") or "unknown"),
            score=int(status_data.get("score") or 0),
            summary=str(status_data.get("summary") or ""),
            signals=signals,
            candidate_actions=actions,
            blockers=list(dict.fromkeys(str(item) for item in blockers if item)),
            metadata={
                "growth_status": status_data,
                "execution_plan": execution_data,
                "closed_loop": loop_data,
            },
        )


class GrowthChannelTwinProvider:
    """Compose an Autopilot channel twin from existing Growth read models."""

    def __init__(self, growth_service, db) -> None:
        self._growth_service = growth_service
        self._db = db

    async def build_channel_twin(
        self,
        channel_id: str,
        *,
        horizon_days: int = 30,
    ) -> ChannelTwinSnapshot:
        channel_uuid = UUID(channel_id)
        intelligence = await self._growth_service.build_channel_intelligence_snapshot(self._db, channel_uuid)
        workspace = await self._growth_service.get_channel_workspace(
            self._db,
            channel_uuid,
            horizon_days=horizon_days,
        )

        intelligence_data = intelligence.to_dict()
        workspace_data = workspace.to_dict()
        strategy = intelligence_data.get("strategy_context") or workspace_data.get("strategy") or {}
        profile = workspace_data.get("profile") or {
            "channel_id": intelligence_data.get("channel_id"),
            "project_id": intelligence_data.get("project_id"),
            "platform": intelligence_data.get("platform"),
            "name": intelligence_data.get("name"),
            "score": intelligence_data.get("score"),
        }
        objectives = build_objective_tree(
            project_id=str(intelligence_data.get("project_id") or ""),
            strategy=strategy,
            channels=[profile],
        )

        closed_loop = None
        project_id = intelligence_data.get("project_id")
        if project_id:
            try:
                closed_loop = await self._growth_service.build_closed_loop_report(
                    self._db,
                    UUID(str(project_id)),
                    sync_performance=False,
                    horizon_days=horizon_days,
                    persist_report=False,
                )
            except (LookupError, RuntimeError, TypeError, ValueError):
                closed_loop = None

        return build_channel_twin_snapshot(
            channel_intelligence=intelligence,
            workspace=workspace,
            objectives=objectives,
            closed_loop=closed_loop,
        )


class GrowthMarketIntelligenceProvider:
    """Build market opportunities from existing Growth data."""

    def __init__(self, growth_service, db) -> None:
        self._growth_service = growth_service
        self._db = db

    async def build_report(
        self,
        project_id: str,
        *,
        channel_id: str | None = None,
        horizon_days: int = 30,
        external_signals: list[dict] | None = None,
    ) -> MarketIntelligenceReport:
        project_uuid = UUID(project_id)
        channel_uuid = UUID(channel_id) if channel_id else None
        strategy = await self._growth_service.get_strategy(project_uuid, channel_id=channel_uuid)
        calendar = await self._growth_service.get_content_calendar(
            project_uuid,
            horizon_days=horizon_days,
            channel_id=channel_uuid,
        )
        competitors = await self._growth_service.list_competitors(project_uuid)
        twin = None
        if channel_id:
            twin = await GrowthChannelTwinProvider(self._growth_service, self._db).build_channel_twin(
                channel_id,
                horizon_days=horizon_days,
            )
        return build_market_intelligence_report(
            project_id=project_id,
            strategy=strategy,
            calendar=calendar,
            competitors=[competitor.to_dict() for competitor in competitors],
            channel_twin=twin,
            external_signals=external_signals or [],
        )

    def recommendations_from_report(self, report: MarketIntelligenceReport) -> list:
        from contentos_growth.domain import GrowthRecommendation

        recommendations: list[GrowthRecommendation] = []
        for opportunity in report.opportunities:
            recommendations.append(
                GrowthRecommendation(
                    id=None,
                    project_id=report.project_id,
                    channel_id=None,
                    kind="market_trend",
                    title=opportunity.title,
                    detail=opportunity.recommendation,
                    priority=opportunity.priority,
                    source="market_intelligence",
                )
            )
        return recommendations
