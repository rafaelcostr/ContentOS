"""Growth history timeline — Growth OS Fase 17."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contentos_growth.domain import ChannelProfile


@dataclass(frozen=True)
class GrowthHistoryEvent:
    id: str
    project_id: str
    channel_id: str | None
    kind: str
    title: str
    detail: str
    status: str
    occurred_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "channel_id": self.channel_id,
            "kind": self.kind,
            "title": self.title,
            "detail": self.detail,
            "status": self.status,
            "occurred_at": self.occurred_at,
            "metadata": dict(self.metadata),
        }


def _event_time(item: dict[str, Any]) -> str:
    for key in ("occurred_at", "created_at", "planned_for", "analyzed_at", "updated_at"):
        value = item.get(key)
        if value:
            return str(value)
    return ""


def build_growth_history(
    *,
    project_id: str,
    calendar_items: list[dict[str, Any]],
    posts: list[dict[str, Any]],
    schedules: list[dict[str, Any]],
    channels: list[ChannelProfile],
    reports: list[dict[str, Any]] | None = None,
) -> list[GrowthHistoryEvent]:
    events: list[GrowthHistoryEvent] = []

    for item in calendar_items:
        item_id = str(item.get("id") or "")
        if not item_id:
            continue
        metadata = item.get("metadata") or {}
        status = str(item.get("status") or "planned")
        if status not in ("dispatched", "scheduled", "pending_schedule", "post_ready", "post_generated"):
            continue
        kind = "dispatch" if status == "dispatched" else "schedule" if "schedule" in status else "post"
        events.append(
            GrowthHistoryEvent(
                id=f"cal-{item_id}",
                project_id=project_id,
                channel_id=item.get("channel_id"),
                kind=kind,
                title=str(item.get("title") or item.get("topic") or "Calendário"),
                detail=f"Status: {status}",
                status=status,
                occurred_at=_event_time(item) or _event_time(metadata),
                metadata={
                    "platform": metadata.get("platform"),
                    "content_type": metadata.get("content_type"),
                    "pipeline_id": metadata.get("pipeline_id"),
                    "schedule_id": metadata.get("schedule_id"),
                },
            )
        )

    for post in posts:
        post_id = str(post.get("id") or "")
        if not post_id:
            continue
        metadata = post.get("metadata") or {}
        events.append(
            GrowthHistoryEvent(
                id=f"post-{post_id}",
                project_id=project_id,
                channel_id=post.get("channel_id"),
                kind="post",
                title=str(post.get("title") or post.get("topic") or "Post gerado"),
                detail="Artefatos Multi Content",
                status=str(post.get("status") or "post_ready"),
                occurred_at=_event_time(metadata) or _event_time(post),
                metadata={
                    "formats": metadata.get("post_formats"),
                    "artifact_count": len(metadata.get("post_artifacts") or []),
                },
            )
        )

    for schedule in schedules:
        schedule_id = str(schedule.get("id") or schedule.get("schedule_id") or "")
        if not schedule_id:
            continue
        events.append(
            GrowthHistoryEvent(
                id=f"sch-{schedule_id}",
                project_id=project_id,
                channel_id=None,
                kind="schedule",
                title=str(schedule.get("name") or schedule.get("topic") or "Agendamento"),
                detail=f"Cron: {schedule.get('cron_expression', '—')}",
                status="active" if schedule.get("is_active") else "pending",
                occurred_at=str(schedule.get("next_run_at") or ""),
                metadata={
                    "calendar_item_id": schedule.get("calendar_item_id"),
                    "timezone": schedule.get("timezone"),
                },
            )
        )

    for channel in channels:
        if not channel.analyzed_at:
            continue
        events.append(
            GrowthHistoryEvent(
                id=f"ana-{channel.channel_id}",
                project_id=project_id,
                channel_id=channel.channel_id,
                kind="analysis",
                title=f"Análise: {channel.name}",
                detail=f"Score {channel.score:.0f}/100",
                status="completed",
                occurred_at=channel.analyzed_at,
                metadata={"platform": channel.platform},
            )
        )

    for report in reports or []:
        report_id = str(report.get("id") or "")
        if not report_id:
            continue
        events.append(
            GrowthHistoryEvent(
                id=f"rep-{report_id}",
                project_id=project_id,
                channel_id=report.get("channel_id"),
                kind="report",
                title="Growth Report",
                detail=str(report.get("summary") or "")[:200],
                status="generated",
                occurred_at=str(report.get("created_at") or ""),
                metadata={"score": report.get("score")},
            )
        )

    events.sort(key=lambda event: event.occurred_at or "", reverse=True)
    return events
