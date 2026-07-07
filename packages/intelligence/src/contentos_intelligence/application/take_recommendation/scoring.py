"""Multi-signal scoring for take recommendation (V5.0.4)."""

from __future__ import annotations

import os
import re
from typing import Any


def query_tokens(*values: Any) -> set[str]:
    text = " ".join(str(v) for v in values if v)
    return {part.lower() for part in re.findall(r"[\wÀ-ÿ]{3,}", text)}


def asset_text(meta: dict[str, Any], tags: list[str], object_key: str, content_type: str) -> str:
    return " ".join(
        [
            object_key or "",
            content_type or "",
            " ".join(str(t) for t in tags),
            " ".join(str(v) for v in meta.values() if not isinstance(v, (dict, list))),
            " ".join(str(v) for v in meta.get("objects", []) if isinstance(meta.get("objects"), list)),
        ]
    ).lower()


def score_semantic(cosine: float) -> tuple[float, str | None]:
    weight = float(os.getenv("TAKE_SCORE_SEMANTIC_WEIGHT", "40"))
    if cosine <= 0:
        return 0.0, None
    return cosine * weight, f"semantic:{cosine:.2f}"


def score_tokens(query_tokens_set: set[str], haystack: str) -> tuple[float, str | None]:
    if not query_tokens_set:
        return 0.0, None
    hits = sorted(token for token in query_tokens_set if token in haystack)
    if not hits:
        return 0.0, None
    points = min(len(hits), 8) * 5
    return float(points), f"tokens:{', '.join(hits[:5])}"


def score_media_fields(query_tokens_set: set[str], meta: dict[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    points = 0.0
    analysis = meta.get("media_analysis") if isinstance(meta.get("media_analysis"), dict) else {}
    for field in ("scenario", "emotion", "motion", "time_of_day", "camera_type", "angle"):
        value = str(meta.get(field) or analysis.get(field) or "").lower()
        if value and any(token in value for token in query_tokens_set):
            points += 12
            reasons.append(f"media:{field}")
    return points, reasons


def score_quality(size_bytes: int, meta: dict[str, Any]) -> tuple[float, str | None]:
    points = 0.0
    if size_bytes >= 5_000_000:
        points += 15
    elif size_bytes >= 1_000_000:
        points += 10
    elif size_bytes >= 250_000:
        points += 5
    width = meta.get("width") or meta.get("video_width")
    if width and int(width) >= 1080:
        points += 5
    if points <= 0:
        return 0.0, None
    return points, "quality"


def score_duration_fit(duration_needed: float | None, meta: dict[str, Any]) -> tuple[float, str | None]:
    if not duration_needed:
        return 0.0, None
    raw = meta.get("duration_seconds") or meta.get("duration")
    if raw is None:
        analysis = meta.get("media_analysis") if isinstance(meta.get("media_analysis"), dict) else {}
        raw = analysis.get("duration_seconds")
    try:
        asset_duration = float(raw)
    except (TypeError, ValueError):
        return 0.0, None
    if asset_duration <= 0:
        return 0.0, None
    ratio = min(duration_needed, asset_duration) / max(duration_needed, asset_duration)
    if ratio < 0.4:
        return 0.0, None
    return ratio * 10, f"duration:{ratio:.2f}"


def score_motion_fit(scene_motion: str | None, meta: dict[str, Any]) -> tuple[float, str | None]:
    if not scene_motion:
        return 0.0, None
    analysis = meta.get("media_analysis") if isinstance(meta.get("media_analysis"), dict) else {}
    asset_motion = str(meta.get("motion") or analysis.get("motion") or "").lower()
    if not asset_motion:
        return 0.0, None
    scene_motion = scene_motion.lower()
    if scene_motion in asset_motion or asset_motion in scene_motion:
        return 8.0, "motion-fit"
    return 0.0, None
