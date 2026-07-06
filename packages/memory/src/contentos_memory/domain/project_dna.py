"""Project DNA constants and helpers — Epic 8 V4."""

from __future__ import annotations

VALID_PACES = frozenset({"slow", "medium", "fast"})

PACE_LABELS = {
    "slow": "lento",
    "medium": "médio",
    "fast": "rápido",
}

VALID_FORMATS = frozenset({
    "tiktok",
    "youtube_shorts",
    "instagram_reels",
    "article",
    "newsletter",
    "thread_x",
    "linkedin",
    "carousel",
    "podcast",
    "email_marketing",
})


def normalize_pace(value: str | None) -> str:
    if not value:
        return ""
    pace = value.strip().lower()
    return pace if pace in VALID_PACES else ""


def clamp_humor_level(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))
