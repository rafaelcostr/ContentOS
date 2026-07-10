"""Growth E2E flow tests (in-process) — Fase 18."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from contentos_growth.application.channel_manager import ChannelManagerSignals, build_channel_daily_plan
from contentos_growth.application.growth_hardening import audit_channel_oauth, build_growth_health
from contentos_growth.application.growth_history_builder import build_growth_history
from contentos_growth.application.growth_report_builder import GrowthReportSignals, assemble_growth_report
from contentos_growth.application.multi_channel_scope import build_channel_overview_item, filter_calendar_by_channel
from contentos_growth.domain import ChannelProfile, GrowthStrategy

PROJECT_ID = str(uuid4())
CHANNEL_ID = str(uuid4())


def _future_calendar_item() -> dict:
    return {
        "id": str(uuid4()),
        "project_id": PROJECT_ID,
        "channel_id": CHANNEL_ID,
        "title": "Short E2E",
        "topic": "Produtividade",
        "planned_for": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "status": "planned",
        "metadata": {"platform": "youtube", "content_type": "short"},
    }


def test_growth_e2e_decision_pipeline():
    """Strategy signals → channel plan → scoped calendar → health."""
    channel = ChannelProfile(
        channel_id=CHANNEL_ID,
        project_id=PROJECT_ID,
        platform="youtube",
        name="E2E Channel",
        score=70,
        has_credentials=True,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
    )
    calendar_item = _future_calendar_item()
    calendar = [calendar_item]
    scoped = filter_calendar_by_channel(calendar, CHANNEL_ID)
    assert len(scoped) == 1

    signals = ChannelManagerSignals(
        channel_id=CHANNEL_ID,
        project_id=PROJECT_ID,
        platform="youtube",
        channel_name=channel.name,
        channel_score=channel.score,
        has_credentials=True,
        calendar_items=scoped,
        posting_gap_days=2.0,
    )
    plan = build_channel_daily_plan(signals, strategy=GrowthStrategy(project_id=PROJECT_ID, positioning="E2E"))
    assert plan.actions

    overview = build_channel_overview_item(
        channel,
        calendar=scoped,
        recommendations=[],
        performance=[],
    )
    assert overview.health_status in ("healthy", "attention", "critical")

    oauth = audit_channel_oauth(
        channel_id=CHANNEL_ID,
        project_id=PROJECT_ID,
        platform="youtube",
        channel_name=channel.name,
        credentials={"access_token": "tok", "refresh_token": "ref", "expires_at": "2099-01-01T00:00:00+00:00"},
    )
    health = build_growth_health(
        checks={"database": True, "workflow_engine": True},
        oauth_audits=[oauth],
    )
    assert health.status == "healthy"


def test_growth_e2e_report_and_history():
    channel = ChannelProfile(
        channel_id=CHANNEL_ID,
        project_id=PROJECT_ID,
        platform="youtube",
        name="E2E Channel",
        score=75,
        has_credentials=True,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
    )
    dispatched = {
        **_future_calendar_item(),
        "status": "dispatched",
        "metadata": {"platform": "youtube", "pipeline_id": str(uuid4())},
    }
    history = build_growth_history(
        project_id=PROJECT_ID,
        calendar_items=[dispatched],
        posts=[],
        schedules=[],
        channels=[channel],
    )
    assert any(event.kind == "dispatch" for event in history)

    report = assemble_growth_report(
        project_id=UUID(PROJECT_ID),
        channels=[channel],
        competitors=[],
        stored_recommendations=[],
        base_strategy=GrowthStrategy(project_id=PROJECT_ID, positioning="E2E test"),
        signals=GrowthReportSignals(memory_mission="Test mission"),
    )
    assert report.score >= 0
    assert report.summary
