"""Growth repository protocol."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from contentos_growth.domain import ChannelProfile, CompetitorProfile, GrowthRecommendation, GrowthStrategy


class GrowthRepository(Protocol):
    async def list_channel_profiles(self, project_id: UUID) -> list[ChannelProfile]: ...

    async def get_channel_profile(self, channel_id: UUID) -> ChannelProfile | None: ...

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
    ) -> ChannelProfile: ...

    async def list_channel_analysis_history(self, channel_id: UUID, *, limit: int = 20) -> list[dict]: ...

    async def list_competitors(self, project_id: UUID) -> list[CompetitorProfile]: ...

    async def create_competitor(
        self,
        project_id: UUID,
        *,
        platform: str,
        handle: str,
        display_name: str,
        url: str | None = None,
        notes: str = "",
    ) -> CompetitorProfile: ...

    async def get_competitor(self, competitor_id: UUID) -> CompetitorProfile | None: ...

    async def update_competitor(
        self,
        competitor_id: UUID,
        *,
        metrics: dict | None = None,
        display_name: str | None = None,
        url: str | None = None,
    ) -> CompetitorProfile: ...

    async def save_competitor_recommendations(
        self,
        *,
        project_id: UUID,
        competitor_id: UUID,
        recommendations: list[GrowthRecommendation],
    ) -> None: ...

    async def list_recommendations(
        self,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
    ) -> list[GrowthRecommendation]: ...

    async def save_recommendations(self, project_id: UUID, recommendations: list[GrowthRecommendation]) -> int: ...

    async def get_strategy(
        self,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
    ) -> GrowthStrategy | None: ...

    async def save_project_report(
        self,
        *,
        project_id: UUID,
        score: float,
        summary: str,
        report: dict,
    ) -> None: ...

    async def save_strategy(self, project_id: UUID, strategy: GrowthStrategy, *, status: str = "active") -> GrowthStrategy: ...

    async def list_calendar_items(
        self,
        project_id: UUID,
        *,
        horizon_days: int = 30,
        channel_id: UUID | None = None,
    ) -> list[dict]: ...

    async def replace_calendar_items(self, project_id: UUID, items: list[dict]) -> list[dict]: ...

    async def create_calendar_items(self, project_id: UUID, items: list[dict]) -> list[dict]: ...

    async def get_calendar_item(self, calendar_item_id: UUID) -> dict | None: ...

    async def list_planned_calendar_items(self, project_id: UUID, *, limit: int = 10) -> list[dict]: ...

    async def mark_calendar_dispatched(
        self,
        calendar_item_id: UUID,
        *,
        pipeline_id: UUID,
        status: str = "dispatched",
    ) -> dict: ...

    async def mark_calendar_post_generated(
        self,
        calendar_item_id: UUID,
        *,
        artifacts: list[dict],
        formats: list[str],
        status: str | None = "post_ready",
        companion: bool = False,
    ) -> dict: ...

    async def list_calendar_posts(self, project_id: UUID, *, limit: int = 50) -> list[dict]: ...

    async def mark_calendar_scheduled(
        self,
        calendar_item_id: UUID,
        *,
        schedule_id: UUID,
        mode: str,
        cron_expression: str,
        status: str = "pending_schedule",
    ) -> dict: ...

    async def list_scheduled_calendar_items(self, project_id: UUID, *, limit: int = 50) -> list[dict]: ...

    async def save_channel_manager_plan(self, channel_id: UUID, plan: dict[str, Any]) -> None: ...

    async def list_asset_performance(
        self,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
        limit: int = 20,
    ) -> list[dict]: ...

    async def list_project_report_history(self, project_id: UUID, *, limit: int = 30) -> list[dict]: ...
