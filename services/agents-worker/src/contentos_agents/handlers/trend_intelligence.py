"""Trend Intelligence Agent — memory + analytics → research patterns + forecast (V3 B9 / V4.2.4)."""

from __future__ import annotations

import json

from contentos_intelligence.application.trend_forecast import TrendForecastService, is_trend_forecast_enabled
from contentos_intelligence.infrastructure.trend_forecast_repository import (
    TrendForecastRepository,
    count_kb_entries_sync,
    list_learning_insights_sync,
)
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import AssetCategory, JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput
from contentos_shared.schemas.asset import AssetMeta
from contentos_shared.trend_intelligence import build_trend_brief, format_trend_context

try:
    from contentos_analytics_ai.infrastructure.db_repository import list_by_project_sync
except ImportError:

    def list_by_project_sync(project_id, limit=10):  # type: ignore[misc]
        return []

try:
    from contentos_memory import get_memory_service
except ImportError:

    def get_memory_service():  # type: ignore[misc]
        return None

try:
    from contentos_events import DomainEvent, get_event_bus
    from contentos_events.domain.event_types import TREND_FORECASTED
except ImportError:
    DomainEvent = None  # type: ignore[misc, assignment]
    TREND_FORECASTED = "trend.forecasted"  # type: ignore[misc]

    def get_event_bus():  # type: ignore[misc]
        return None


class TrendIntelligenceAgentHandler(BaseAgentHandler):
    step = "trend_intelligence"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        topic = str(task_input.payload.get("topic") or "")
        niche = str(task_input.payload.get("niche") or "")
        logs = [f"[trend_intelligence] Building trend brief for: {topic}"]

        memory = None
        memory_svc = get_memory_service()
        if memory_svc:
            memory = memory_svc.get_memory(task_input.project_id)
            if not niche and memory.niche:
                niche = memory.niche
            logs.append("Project memory loaded")

        insights = list_by_project_sync(task_input.project_id, limit=10)
        logs.append(f"Analytics insights: {len(insights)}")

        trend_brief = build_trend_brief(
            topic=topic,
            niche=niche,
            memory=memory,
            insights=insights,
        )
        trend_context = format_trend_context(trend_brief)

        forecast_report = None
        if is_trend_forecast_enabled():
            learning_rows = list_learning_insights_sync(task_input.project_id, limit=10)
            kb_count = count_kb_entries_sync(task_input.project_id)
            forecast_report = TrendForecastService().forecast(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                topic=topic,
                niche=niche,
                memory=memory,
                insights=insights,
                learning_rows=learning_rows,
                kb_entry_count=kb_count,
                trend_brief=trend_brief,
            )
            trend_brief["trend_score"] = forecast_report.trend_score
            trend_brief["expected_growth"] = forecast_report.expected_growth
            trend_brief["production_recommendation"] = forecast_report.production_recommendation
            TrendForecastRepository().save_report_sync(forecast_report)
            logs.append(
                f"Forecast: score={forecast_report.trend_score:.0f} "
                f"growth={forecast_report.expected_growth}"
            )
            self._publish_forecast_event(task_input, forecast_report.to_dict())

        logs.append(
            f"Brief: {len(trend_brief['patterns'])} patterns, "
            f"pacing={trend_brief['pacing_hint']}, sources={trend_brief['sources']}"
        )

        ref = await self.get_asset_manager().store(
            AssetCategory.SCRIPTS,
            json.dumps(trend_brief, ensure_ascii=False).encode(),
            AssetMeta(
                project_id=task_input.project_id,
                pipeline_id=task_input.pipeline_id,
                filename="trend_brief.json",
                content_type="application/json",
            ),
        )

        data: dict = {
            "trend_brief": trend_brief,
            "trend_patterns": trend_brief["patterns"],
            "trend_context": trend_context,
            "recommended_hooks": trend_brief["recommended_hooks"],
            "trend_pacing": trend_brief["pacing_hint"],
        }
        if forecast_report:
            data.update(
                {
                    "trend_score": forecast_report.trend_score,
                    "expected_growth": forecast_report.expected_growth,
                    "production_recommendation": forecast_report.production_recommendation,
                    "trend_forecast_report": forecast_report.to_dict(),
                }
            )

        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            artifacts=[ref],
            data=data,
            logs=logs,
        )

    def _publish_forecast_event(self, task_input: AgentTaskInput, report: dict) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent:
                return
            event = DomainEvent(
                event_type=TREND_FORECASTED,
                pipeline_id=task_input.pipeline_id,
                project_id=task_input.project_id,
                job_id=task_input.job_id,
                agent="trend_intelligence",
                step=self.step,
                status="completed",
                payload=report,
            )
            bus.publish_sync(event)
        except Exception:
            pass
