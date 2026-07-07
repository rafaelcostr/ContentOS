"""Merge vision JSON into searchable asset metadata facets."""

from __future__ import annotations

from typing import Any


def normalize_media_analysis(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {}
    analysis = {
        "objects": _list(raw.get("objects")),
        "characters": _list(raw.get("characters")),
        "vehicles": _list(raw.get("vehicles")),
        "colors": _list(raw.get("colors")),
        "scenario": _str(raw.get("scenario")),
        "motion": _str(raw.get("motion")),
        "speed": _str(raw.get("speed")),
        "time_of_day": _str(raw.get("time_of_day")),
        "angle": _str(raw.get("angle")),
        "emotion": _str(raw.get("emotion")),
        "camera_type": _str(raw.get("camera_type")),
    }
    return {k: v for k, v in analysis.items() if v}


def analysis_to_metadata(analysis: dict[str, Any]) -> dict[str, Any]:
    """Map analysis fields onto Asset.metadata_ search facets."""
    meta: dict[str, Any] = {"media_analysis": analysis}
    if analysis.get("scenario"):
        meta["scenario"] = analysis["scenario"]
    if analysis.get("motion"):
        meta["motion"] = analysis["motion"]
    if analysis.get("emotion"):
        meta["emotion"] = analysis["emotion"]
    if analysis.get("time_of_day"):
        meta["time_of_day"] = analysis["time_of_day"]
    if analysis.get("angle"):
        meta["angle"] = analysis["angle"]
    if analysis.get("camera_type"):
        meta["camera_type"] = analysis["camera_type"]
    if analysis.get("colors"):
        meta["color"] = ", ".join(analysis["colors"][:3])
    objects: list[str] = []
    for key in ("objects", "characters", "vehicles"):
        objects.extend(analysis.get(key) or [])
    if objects:
        meta["objects"] = objects[:20]
    return meta


def analysis_summary_text(analysis: dict[str, Any], *, topic: str = "") -> str:
    parts = [topic] if topic else []
    for key in ("scenario", "motion", "emotion", "time_of_day", "camera_type", "angle", "color"):
        value = analysis.get(key)
        if value:
            parts.append(str(value))
    for key in ("objects", "characters", "vehicles", "colors"):
        items = analysis.get(key) or []
        if items:
            parts.append(", ".join(str(i) for i in items[:8]))
    return ". ".join(p for p in parts if p)


def merge_vision_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    list_keys = ("objects", "characters", "vehicles", "colors")
    for result in results:
        norm = normalize_media_analysis(result)
        for key in list_keys:
            bucket = merged.setdefault(key, [])
            for item in norm.get(key, []):
                if item not in bucket:
                    bucket.append(item)
        for key, value in norm.items():
            if key in list_keys:
                continue
            if value and not merged.get(key):
                merged[key] = value
    return normalize_media_analysis(merged)


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.replace(";", ",").split(",") if v.strip()]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
