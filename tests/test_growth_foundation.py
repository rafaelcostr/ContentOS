"""Growth AI foundation tests."""

from __future__ import annotations

from uuid import UUID

import pytest
from contentos_growth.application.service import GrowthService
from contentos_growth.domain import ChannelProfile, CompetitorProfile, GrowthRecommendation

PROJECT_ID = UUID("00000000-0000-0000-0000-000000000101")


class FakeGrowthRepository:
    def __init__(self):
        self.channels: list[ChannelProfile] = []
        self.competitors: list[CompetitorProfile] = []
        self.recommendations: list[GrowthRecommendation] = []

    async def list_channel_profiles(self, project_id: UUID) -> list[ChannelProfile]:
        return self.channels

    async def list_competitors(self, project_id: UUID) -> list[CompetitorProfile]:
        return self.competitors

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
        competitor = CompetitorProfile(
            id="c1",
            project_id=str(project_id),
            platform=platform,
            handle=handle,
            display_name=display_name,
            url=url,
            notes=notes,
        )
        self.competitors.append(competitor)
        return competitor

    async def list_recommendations(
        self,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
    ) -> list[GrowthRecommendation]:
        return self.recommendations

    async def get_strategy(self, project_id: UUID, *, channel_id: UUID | None = None):
        return None

    async def list_calendar_items(
        self,
        project_id: UUID,
        *,
        horizon_days: int = 30,
        channel_id: UUID | None = None,
    ) -> list[dict]:
        return []

    async def list_asset_performance(
        self,
        project_id: UUID,
        *,
        channel_id: UUID | None = None,
        limit: int = 20,
    ) -> list[dict]:
        return []

    async def get_channel_profile(self, channel_id: UUID):
        return None

    async def list_project_report_history(self, project_id: UUID, *, limit: int = 30) -> list[dict]:
        return []

    async def save_project_report(self, *, project_id: UUID, score: float, summary: str, report: dict) -> None:
        return None


async def test_growth_service_default_recommendation_without_channels():
    service = GrowthService(FakeGrowthRepository())
    recs = await service.list_recommendations(PROJECT_ID)
    assert len(recs) == 1
    assert recs[0].kind == "channel"
    assert recs[0].priority == "high"


async def test_growth_service_creates_competitor_and_report(monkeypatch: pytest.MonkeyPatch):
    from unittest.mock import AsyncMock

    from contentos_growth.application.growth_report_builder import GrowthReportSignals

    async def _fake_gather(db, project_id):  # noqa: ARG001
        return GrowthReportSignals()

    monkeypatch.setattr(
        "contentos_growth.application.service.gather_growth_report_signals",
        _fake_gather,
    )

    repo = FakeGrowthRepository()
    repo.channels.append(
        ChannelProfile(
            channel_id="ch1",
            project_id=str(PROJECT_ID),
            platform="youtube",
            name="Main Channel",
            score=70,
        )
    )
    service = GrowthService(repo)
    competitor = await service.create_competitor(
        PROJECT_ID,
        platform="YouTube",
        handle="@rival",
        display_name="Rival",
    )
    report = await service.build_report(AsyncMock(), PROJECT_ID, persist=False)
    data = report.to_dict()
    assert competitor.platform == "youtube"
    assert data["score"] > 40
    assert len(data["channels"]) == 1
    assert len(data["competitors"]) == 1
    assert data["strategy"]["goals"]


def test_growth_database_models_registered():
    from contentos_database.models import (
        GrowthAssetPerformanceRow,
        GrowthChannelProfileRow,
        GrowthCompetitorRow,
        GrowthContentCalendarRow,
        GrowthRecommendationRow,
        GrowthReportRow,
        GrowthStrategyRow,
    )

    assert GrowthChannelProfileRow.__tablename__ == "growth_channel_profiles"
    assert GrowthCompetitorRow.__tablename__ == "growth_competitors"
    assert GrowthReportRow.__tablename__ == "growth_reports"
    assert GrowthStrategyRow.__tablename__ == "growth_strategies"
    assert GrowthRecommendationRow.__tablename__ == "growth_recommendations"
    assert GrowthAssetPerformanceRow.__tablename__ == "growth_asset_performance"
    assert GrowthContentCalendarRow.__tablename__ == "growth_content_calendar"
