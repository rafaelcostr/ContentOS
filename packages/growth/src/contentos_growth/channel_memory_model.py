"""Channel memory domain — per-channel patterns (Growth OS Fase 6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


def _normalize_string_list(value: list | None, *, limit: int = 24) -> list[str]:
    if not value:
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out[:limit]


def _normalize_video_entries(value: list | None, *, limit: int = 10) -> list[dict[str, Any]]:
    if not value:
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        entry: dict[str, Any] = {"title": title[:300]}
        for key in ("external_id", "engagement_rate", "views", "media_kind", "note"):
            if item.get(key) is not None:
                entry[key] = item[key]
        out.append(entry)
        if len(out) >= limit:
            break
    return out


def _normalize_hours(value: list | None) -> list[int]:
    if not value:
        return []
    hours: list[int] = []
    for raw in value:
        try:
            hour = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= hour <= 23 and hour not in hours:
            hours.append(hour)
    return sorted(hours)[:12]


@dataclass
class ChannelMemoryData:
    channel_id: UUID
    project_id: UUID
    winning_videos: list[dict[str, Any]] = field(default_factory=list)
    losing_videos: list[dict[str, Any]] = field(default_factory=list)
    top_hooks: list[str] = field(default_factory=list)
    top_ctas: list[str] = field(default_factory=list)
    top_themes: list[str] = field(default_factory=list)
    top_hashtags: list[str] = field(default_factory=list)
    best_posting_hours: list[int] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    notes: str = ""

    def format_channel_context(self) -> str:
        """Compact block for {{channel_context}} in prompts."""
        parts: list[str] = []
        if self.top_hooks:
            parts.append(f"Hooks que funcionam: {', '.join(self.top_hooks[:6])}")
        if self.top_ctas:
            parts.append(f"CTAs eficazes: {', '.join(self.top_ctas[:6])}")
        if self.top_themes:
            parts.append(f"Temas recorrentes: {', '.join(self.top_themes[:8])}")
        if self.top_hashtags:
            parts.append(f"Hashtags: {', '.join(self.top_hashtags[:10])}")
        if self.best_posting_hours:
            hours = ", ".join(f"{h}h" for h in self.best_posting_hours[:6])
            parts.append(f"Melhores horários: {hours}")
        if self.winning_videos:
            titles = [v.get("title", "") for v in self.winning_videos[:3] if v.get("title")]
            if titles:
                parts.append(f"Vídeos vencedores: {' | '.join(titles)}")
        if self.losing_videos:
            titles = [v.get("title", "") for v in self.losing_videos[:2] if v.get("title")]
            if titles:
                parts.append(f"Evitar padrões de: {' | '.join(titles)}")
        if self.insights:
            parts.append(f"Insights: {' | '.join(self.insights[:4])}")
        if self.notes.strip():
            parts.append(f"Notas: {self.notes.strip()[:400]}")
        return ". ".join(parts) + ("." if parts else "")

    def apply_patch(self, patch: dict[str, Any]) -> None:
        if "winning_videos" in patch and patch["winning_videos"] is not None:
            self.winning_videos = _normalize_video_entries(patch["winning_videos"])
        if "losing_videos" in patch and patch["losing_videos"] is not None:
            self.losing_videos = _normalize_video_entries(patch["losing_videos"])
        if "top_hooks" in patch and patch["top_hooks"] is not None:
            self.top_hooks = _normalize_string_list(patch["top_hooks"], limit=16)
        if "top_ctas" in patch and patch["top_ctas"] is not None:
            self.top_ctas = _normalize_string_list(patch["top_ctas"], limit=16)
        if "top_themes" in patch and patch["top_themes"] is not None:
            self.top_themes = _normalize_string_list(patch["top_themes"], limit=16)
        if "top_hashtags" in patch and patch["top_hashtags"] is not None:
            self.top_hashtags = _normalize_string_list(patch["top_hashtags"], limit=24)
        if "best_posting_hours" in patch and patch["best_posting_hours"] is not None:
            self.best_posting_hours = _normalize_hours(patch["best_posting_hours"])
        if "insights" in patch and patch["insights"] is not None:
            self.insights = _normalize_string_list(patch["insights"], limit=20)
        if "notes" in patch and patch["notes"] is not None:
            self.notes = str(patch["notes"]).strip()

    def merge_seed(
        self,
        *,
        winning_videos: list[dict[str, Any]],
        losing_videos: list[dict[str, Any]],
        top_hooks: list[str],
        top_ctas: list[str],
        top_themes: list[str],
        top_hashtags: list[str],
        best_posting_hours: list[int],
        insights: list[str],
    ) -> None:
        """Merge auto-derived patterns from channel analysis (keeps manual notes)."""
        self.winning_videos = _normalize_video_entries(winning_videos)
        self.losing_videos = _normalize_video_entries(losing_videos)
        self.top_hooks = _merge_unique(self.top_hooks, top_hooks, limit=16)
        self.top_ctas = _merge_unique(self.top_ctas, top_ctas, limit=16)
        self.top_themes = _merge_unique(self.top_themes, top_themes, limit=16)
        self.top_hashtags = _merge_unique(self.top_hashtags, top_hashtags, limit=24)
        self.best_posting_hours = _normalize_hours(best_posting_hours or self.best_posting_hours)
        self.insights = _merge_unique(self.insights, insights, limit=20)

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": str(self.channel_id),
            "project_id": str(self.project_id),
            "winning_videos": list(self.winning_videos),
            "losing_videos": list(self.losing_videos),
            "top_hooks": list(self.top_hooks),
            "top_ctas": list(self.top_ctas),
            "top_themes": list(self.top_themes),
            "top_hashtags": list(self.top_hashtags),
            "best_posting_hours": list(self.best_posting_hours),
            "insights": list(self.insights),
            "notes": self.notes,
            "channel_context_preview": self.format_channel_context(),
        }

    @classmethod
    def empty(cls, channel_id: UUID, project_id: UUID) -> ChannelMemoryData:
        return cls(channel_id=channel_id, project_id=project_id)


def _merge_unique(existing: list[str], incoming: list[str], *, limit: int) -> list[str]:
    out = list(existing)
    for item in incoming:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out[:limit]


def _parse_published_hour(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).hour
    except ValueError:
        return None


def extract_patterns_from_media(media_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive winners/losers, hooks and posting hours from platform snapshots."""
    ranked: list[dict[str, Any]] = []
    for item in media_items:
        metrics = item.get("metrics") or {}
        rate = metrics.get("engagement_rate")
        if rate is None:
            continue
        ranked.append(
            {
                "title": str(metrics.get("title") or item.get("title") or "").strip(),
                "external_id": item.get("external_media_id"),
                "engagement_rate": float(rate),
                "views": metrics.get("view_count"),
                "media_kind": metrics.get("media_kind"),
                "published_at": metrics.get("published_at") or item.get("published_at"),
            }
        )
    ranked.sort(key=lambda row: row["engagement_rate"], reverse=True)

    hooks: list[str] = []
    hours: list[int] = []
    themes: list[str] = []
    for row in ranked[:3]:
        title = row.get("title") or ""
        hook = title[:80].strip()
        if hook and hook not in hooks:
            hooks.append(hook)
        hour = _parse_published_hour(row.get("published_at"))
        if hour is not None and hour not in hours:
            hours.append(hour)
        if title and title not in themes:
            themes.append(title[:120])

    winning = [
        {k: v for k, v in row.items() if k != "published_at"}
        for row in ranked[:3]
        if row.get("title")
    ]
    losing = [
        {k: v for k, v in row.items() if k != "published_at"}
        for row in ranked[-3:]
        if row.get("title") and len(ranked) >= 4
    ]

    return {
        "winning_videos": winning,
        "losing_videos": losing,
        "top_hooks": hooks,
        "best_posting_hours": sorted(hours),
        "top_themes": themes[:8],
    }
