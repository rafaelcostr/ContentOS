"""Normalized searchable metadata for Asset Manager V2 (Tier A2)."""

from __future__ import annotations

from typing import Any

# Facets supported by advanced search (stored in Asset.metadata_ JSON)
SEARCH_FACETS = (
    "theme",
    "game",
    "character",
    "motion",
    "color",
    "objects",
    "label",
    "scene_label",
    "source_id",
)


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [p.strip() for p in value.replace(";", ",").split(",")]
        return [p for p in parts if p]
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            text = _as_str(item)
            if text:
                out.append(text)
        return out
    return []


def normalize_asset_metadata(
    *,
    topic: str | None = None,
    scene: dict[str, Any] | None = None,
    candidate: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable metadata dict for search facets.

    Pulls from topic, scene planner fields, content-source candidates, and explicit extras.
    """
    meta: dict[str, Any] = {}
    scene = scene or {}
    candidate = candidate or {}
    candidate_meta = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    extra = extra or {}

    sources: list[dict[str, Any]] = [extra, candidate_meta, candidate, scene]

    theme = _as_str(topic) or _as_str(extra.get("theme")) or _as_str(scene.get("theme"))
    if theme:
        meta["theme"] = theme

    label = (
        _as_str(scene.get("label"))
        or _as_str(scene.get("scene_label"))
        or _as_str(candidate.get("scene_label"))
        or _as_str(extra.get("label"))
    )
    if label:
        meta["label"] = label
        meta["scene_label"] = label

    for key in ("game", "character", "motion", "color"):
        for src in sources:
            value = _as_str(src.get(key))
            if value:
                meta[key] = value
                break

    # Infer game/theme from topic heuristics (e.g. "GTA 6")
    if "game" not in meta and theme:
        meta["game"] = theme

    objects = _as_str_list(extra.get("objects"))
    for src in sources:
        objects.extend(_as_str_list(src.get("objects")))
        objects.extend(_as_str_list(src.get("tags")))
        objects.extend(_as_str_list(src.get("keywords")))
    # visual hints become searchable objects/tags
    for src in (scene, candidate, extra):
        for field in ("visual_hint", "visual", "description", "title", "reason"):
            text = _as_str(src.get(field))
            if text:
                objects.append(text)
    # de-dupe preserve order
    seen: set[str] = set()
    unique_objects: list[str] = []
    for item in objects:
        low = item.lower()
        if low in seen:
            continue
        seen.add(low)
        unique_objects.append(item)
    if unique_objects:
        meta["objects"] = unique_objects[:20]

    source_id = _as_str(candidate.get("source_id")) or _as_str(extra.get("source_id"))
    if source_id:
        meta["source_id"] = source_id

    candidate_id = _as_str(candidate.get("candidate_id")) or _as_str(extra.get("candidate_id"))
    if candidate_id:
        meta["candidate_id"] = candidate_id

    return meta


def facet_tags(metadata: dict[str, Any] | None) -> list[str]:
    """Derive searchable tags from metadata facets (theme:GTA 6, game:..., etc.)."""
    if not metadata:
        return []
    tags: list[str] = []
    for key in SEARCH_FACETS:
        if key == "objects":
            for obj in _as_str_list(metadata.get("objects")):
                tag = f"object:{obj}"
                if tag not in tags:
                    tags.append(tag)
            continue
        value = _as_str(metadata.get(key))
        if not value:
            continue
        tag = f"{key}:{value}"
        if tag not in tags:
            tags.append(tag)
        if value not in tags:
            tags.append(value)
    return tags
