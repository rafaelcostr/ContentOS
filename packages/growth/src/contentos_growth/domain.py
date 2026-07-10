"""Growth AI domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChannelProfile:
    channel_id: str
    project_id: str
    platform: str
    name: str
    score: float = 0.0
    profile: dict[str, Any] = field(default_factory=dict)
    report: dict[str, Any] = field(default_factory=dict)
    analyzed_at: str | None = None
    is_active: bool = True
    has_credentials: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "platform": self.platform,
            "name": self.name,
            "score": self.score,
            "profile": dict(self.profile),
            "report": dict(self.report),
            "analyzed_at": self.analyzed_at,
            "is_active": self.is_active,
            "has_credentials": self.has_credentials,
        }


@dataclass(frozen=True)
class CompetitorProfile:
    id: str | None
    project_id: str
    platform: str
    handle: str
    display_name: str
    url: str | None = None
    notes: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "platform": self.platform,
            "handle": self.handle,
            "display_name": self.display_name,
            "url": self.url,
            "notes": self.notes,
            "metrics": dict(self.metrics),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class GrowthRecommendation:
    id: str | None
    project_id: str
    channel_id: str | None
    kind: str
    title: str
    detail: str
    priority: str = "medium"
    source: str = "growth"
    status: str = "open"
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "channel_id": self.channel_id,
            "kind": self.kind,
            "title": self.title,
            "detail": self.detail,
            "priority": self.priority,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class AssetPerformance:
    asset_id: str
    project_id: str
    channel_id: str | None = None
    uses: int = 0
    ctr: float | None = None
    retention_pct: float | None = None
    watch_time_seconds: float | None = None
    engagement_rate: float | None = None
    ai_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "project_id": self.project_id,
            "channel_id": self.channel_id,
            "uses": self.uses,
            "ctr": self.ctr,
            "retention_pct": self.retention_pct,
            "watch_time_seconds": self.watch_time_seconds,
            "engagement_rate": self.engagement_rate,
            "ai_score": self.ai_score,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ContentCalendar:
    project_id: str
    items: list[dict[str, Any]] = field(default_factory=list)
    horizon_days: int = 30

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "horizon_days": self.horizon_days,
            "items": [dict(item) for item in self.items],
        }


@dataclass(frozen=True)
class GrowthStrategy:
    project_id: str
    channel_id: str | None = None
    positioning: str = ""
    goals: list[str] = field(default_factory=list)
    kpis: dict[str, Any] = field(default_factory=dict)
    cadence: dict[str, Any] = field(default_factory=dict)
    calendar: ContentCalendar | None = None
    id: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "channel_id": self.channel_id,
            "positioning": self.positioning,
            "goals": list(self.goals),
            "kpis": dict(self.kpis),
            "cadence": dict(self.cadence),
            "calendar": self.calendar.to_dict() if self.calendar else None,
            "id": self.id,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class GrowthReport:
    project_id: str
    summary: str
    score: float
    channels: list[ChannelProfile] = field(default_factory=list)
    competitors: list[CompetitorProfile] = field(default_factory=list)
    recommendations: list[GrowthRecommendation] = field(default_factory=list)
    strategy: GrowthStrategy | None = None
    generated_at: str = ""
    channel_health: list[dict[str, Any]] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    asset_ranking: list[dict[str, Any]] = field(default_factory=list)
    report_detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "summary": self.summary,
            "score": self.score,
            "channels": [channel.to_dict() for channel in self.channels],
            "competitors": [competitor.to_dict() for competitor in self.competitors],
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "strategy": self.strategy.to_dict() if self.strategy else None,
            "generated_at": self.generated_at,
            "channel_health": [dict(item) for item in self.channel_health],
            "opportunities": list(self.opportunities),
            "risks": list(self.risks),
            "asset_ranking": [dict(item) for item in self.asset_ranking],
            "report_detail": dict(self.report_detail),
        }
