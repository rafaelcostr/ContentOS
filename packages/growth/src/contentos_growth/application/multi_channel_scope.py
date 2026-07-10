"""Multi-channel scope and isolation — Growth OS Fase 16.

Mandatory filter chain: org_id → project_id → channel_id (when applicable).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from contentos_growth.domain import ChannelProfile, CompetitorProfile, GrowthRecommendation, GrowthStrategy


@dataclass(frozen=True)
class ChannelScope:
    org_id: str | None
    project_id: str
    channel_id: str
    platform: str
    channel_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "project_id": self.project_id,
            "channel_id": self.channel_id,
            "platform": self.platform,
            "channel_name": self.channel_name,
        }


@dataclass
class ChannelWorkspace:
    scope: ChannelScope
    profile: ChannelProfile | None = None
    memory: dict[str, Any] = field(default_factory=dict)
    analytics: dict[str, Any] = field(default_factory=dict)
    performance: list[dict[str, Any]] = field(default_factory=list)
    learning: list[dict[str, Any]] = field(default_factory=list)
    calendar: list[dict[str, Any]] = field(default_factory=list)
    strategy: GrowthStrategy | None = None
    recommendations: list[GrowthRecommendation] = field(default_factory=list)
    competitors: list[CompetitorProfile] = field(default_factory=list)
    assets: list[dict[str, Any]] = field(default_factory=list)
    manager_plan: dict[str, Any] | None = None
    summary: str = ""
    health_status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope.to_dict(),
            "profile": self.profile.to_dict() if self.profile else None,
            "memory": dict(self.memory),
            "analytics": dict(self.analytics),
            "performance": list(self.performance),
            "learning": list(self.learning),
            "calendar": list(self.calendar),
            "strategy": self.strategy.to_dict() if self.strategy else None,
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "competitors": [comp.to_dict() for comp in self.competitors],
            "assets": list(self.assets),
            "manager_plan": dict(self.manager_plan) if self.manager_plan else None,
            "summary": self.summary,
            "health_status": self.health_status,
        }


@dataclass(frozen=True)
class ChannelOverviewItem:
    channel_id: str
    project_id: str
    platform: str
    name: str
    score: float
    health_status: str
    calendar_planned: int
    calendar_scheduled: int
    recommendations_open: int
    has_credentials: bool
    is_active: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "platform": self.platform,
            "name": self.name,
            "score": self.score,
            "health_status": self.health_status,
            "calendar_planned": self.calendar_planned,
            "calendar_scheduled": self.calendar_scheduled,
            "recommendations_open": self.recommendations_open,
            "has_credentials": self.has_credentials,
            "is_active": self.is_active,
        }


def item_channel_id(item: dict[str, Any]) -> str | None:
    metadata = item.get("metadata") or {}
    raw = item.get("channel_id") or metadata.get("channel_id")
    return str(raw) if raw else None


def filter_calendar_by_channel(items: list[dict[str, Any]], channel_id: str) -> list[dict[str, Any]]:
    return [item for item in items if item_channel_id(item) == channel_id]


def filter_recommendations_for_channel(
    recommendations: list[GrowthRecommendation],
    channel_id: str,
    *,
    include_project_wide: bool = True,
) -> list[GrowthRecommendation]:
    scoped: list[GrowthRecommendation] = []
    for rec in recommendations:
        if rec.channel_id == channel_id:
            scoped.append(rec)
        elif include_project_wide and not rec.channel_id:
            scoped.append(rec)
    return scoped


def filter_learning_for_platform(rows: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    from contentos_growth.platform_registry import normalize_platform_id

    normalized = normalize_platform_id(platform)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        row_platform = row.get("platform")
        if row_platform is None or normalize_platform_id(str(row_platform)) == normalized:
            filtered.append(row)
    return filtered


def infer_channel_health(
    *,
    profile: ChannelProfile | None,
    calendar: list[dict[str, Any]],
    performance: list[dict[str, Any]],
) -> str:
    score = float(profile.score if profile else 0)
    has_credentials = bool(profile and profile.has_credentials)
    low_perf = sum(1 for row in performance if row.get("performance_tier") == "low")
    planned = sum(1 for item in calendar if item.get("status") == "planned")

    if not has_credentials or score < 40 or low_perf >= 3:
        return "critical"
    if score < 60 or low_perf >= 1 or planned == 0:
        return "attention"
    return "healthy"


def build_workspace_summary(scope: ChannelScope, health_status: str, calendar: list[dict[str, Any]]) -> str:
    planned = sum(1 for item in calendar if item.get("status") == "planned")
    scheduled = sum(1 for item in calendar if item.get("status") in ("scheduled", "pending_schedule"))
    return (
        f"{scope.channel_name} ({scope.platform}) · saúde {health_status} · "
        f"{planned} planejado(s) · {scheduled} agendado(s)"
    )


def build_channel_overview_item(
    profile: ChannelProfile,
    *,
    calendar: list[dict[str, Any]],
    recommendations: list[GrowthRecommendation],
    performance: list[dict[str, Any]],
) -> ChannelOverviewItem:
    health = infer_channel_health(profile=profile, calendar=calendar, performance=performance)
    return ChannelOverviewItem(
        channel_id=profile.channel_id,
        project_id=profile.project_id,
        platform=profile.platform,
        name=profile.name,
        score=float(profile.score or 0),
        health_status=health,
        calendar_planned=sum(1 for item in calendar if item.get("status") == "planned"),
        calendar_scheduled=sum(1 for item in calendar if item.get("status") in ("scheduled", "pending_schedule")),
        recommendations_open=sum(1 for rec in recommendations if rec.status == "open"),
        has_credentials=profile.has_credentials,
        is_active=profile.is_active,
    )


def assert_channel_belongs_to_project(channel_project_id: UUID | str, project_id: UUID | str) -> None:
    if str(channel_project_id) != str(project_id):
        raise ValueError("Channel does not belong to project")
