"""Channel Analyzer — dispatches per-platform heuristics (Growth OS Fase 4/11)."""

from __future__ import annotations

from typing import Any

from contentos_growth.application.channel_analysis_types import ChannelAnalysisResult
from contentos_growth.application.platform_analyzers.instagram import analyze_instagram_channel
from contentos_growth.application.platform_analyzers.tiktok import analyze_tiktok_channel
from contentos_growth.application.platform_analyzers.youtube import analyze_youtube_channel
from contentos_growth.platform_registry import get_platform_profile, normalize_platform_id

__all__ = ["ChannelAnalysisResult", "analyze_channel_snapshot"]
def analyze_channel_snapshot(
    *,
    channel_id: str,
    project_id: str,
    platform: str,
    channel_name: str,
    overview: dict[str, Any] | None,
) -> ChannelAnalysisResult:
    normalized = normalize_platform_id(platform)
    profile = get_platform_profile(normalized)
    label = profile.label if profile else normalized or "plataforma"

    if not overview:
        raise ValueError(f"Nenhum dado sincronizado. Execute a sincronização {label} antes da análise.")

    common = {
        "channel_id": channel_id,
        "project_id": project_id,
        "channel_name": channel_name,
        "overview": overview,
    }

    if normalized == "instagram":
        return analyze_instagram_channel(**common)
    if normalized == "tiktok":
        return analyze_tiktok_channel(**common)
    return analyze_youtube_channel(**common)
