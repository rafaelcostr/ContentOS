"""Growth history builder tests — Growth OS Fase 17."""

from __future__ import annotations

from uuid import uuid4

from contentos_growth.application.growth_history_builder import build_growth_history
from contentos_growth.domain import ChannelProfile


def test_build_growth_history_includes_analysis_and_dispatch():
    project_id = str(uuid4())
    channel_id = str(uuid4())
    channels = [
        ChannelProfile(
            channel_id=channel_id,
            project_id=project_id,
            platform="youtube",
            name="Canal A",
            score=80,
            analyzed_at="2026-07-01T12:00:00+00:00",
        )
    ]
    calendar = [
        {
            "id": str(uuid4()),
            "project_id": project_id,
            "channel_id": channel_id,
            "title": "Short viral",
            "topic": "Produtividade",
            "status": "dispatched",
            "planned_for": "2026-07-02T18:00:00+00:00",
            "metadata": {"platform": "youtube", "pipeline_id": str(uuid4())},
        }
    ]
    events = build_growth_history(
        project_id=project_id,
        calendar_items=calendar,
        posts=[],
        schedules=[],
        channels=channels,
    )
    kinds = {event.kind for event in events}
    assert "analysis" in kinds
    assert "dispatch" in kinds
    assert events[0].occurred_at >= events[-1].occurred_at or len(events) == 1
