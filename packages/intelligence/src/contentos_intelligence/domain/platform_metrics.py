"""Platform OAuth analytics domain — V5.4.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlatformMediaMetrics:
    platform: str
    external_media_id: str | None = None
    title: str | None = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_seconds: float | None = None
    engagement_rate: float | None = None
    published_at: str | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "external_media_id": self.external_media_id,
            "title": self.title,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "watch_time_seconds": self.watch_time_seconds,
            "engagement_rate": self.engagement_rate,
            "published_at": self.published_at,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlatformMediaMetrics:
        return cls(
            platform=str(data.get("platform", "")),
            external_media_id=data.get("external_media_id"),
            title=data.get("title"),
            views=int(data.get("views") or 0),
            likes=int(data.get("likes") or 0),
            comments=int(data.get("comments") or 0),
            shares=int(data.get("shares") or 0),
            watch_time_seconds=data.get("watch_time_seconds"),
            engagement_rate=data.get("engagement_rate"),
            published_at=data.get("published_at"),
            url=data.get("url"),
        )


@dataclass
class PlatformAnalyticsReport:
    platform: str
    channel_id: str
    channel_name: str
    synced: bool
    media_items: list[PlatformMediaMetrics] = field(default_factory=list)
    channel_totals: dict[str, Any] = field(default_factory=dict)
    needs_reconnect: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "synced": self.synced,
            "media_items": [m.to_dict() for m in self.media_items],
            "channel_totals": self.channel_totals,
            "needs_reconnect": self.needs_reconnect,
            "error": self.error,
        }


@dataclass
class PlatformSyncResult:
    project_id: str
    reports: list[PlatformAnalyticsReport] = field(default_factory=list)
    snapshots_saved: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "reports": [r.to_dict() for r in self.reports],
            "snapshots_saved": self.snapshots_saved,
        }
