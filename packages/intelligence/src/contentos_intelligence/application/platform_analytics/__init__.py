"""Platform OAuth analytics — V5.4.1."""

from contentos_intelligence.application.platform_analytics.fetchers import PLATFORM_FETCHERS
from contentos_intelligence.application.platform_analytics.service import (
    build_youtube_connection_status,
    get_latest_channel_overview,
    list_recent_snapshots,
    platform_analytics_enabled,
    platform_analytics_limit,
    summarize_snapshots,
    sync_channel_analytics,
    sync_project_platform_analytics,
)

__all__ = [
    "PLATFORM_FETCHERS",
    "build_youtube_connection_status",
    "get_latest_channel_overview",
    "list_recent_snapshots",
    "platform_analytics_enabled",
    "platform_analytics_limit",
    "summarize_snapshots",
    "sync_channel_analytics",
    "sync_project_platform_analytics",
]
