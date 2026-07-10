"""Brand identity helpers — Growth OS Fase 5 (extends Project DNA)."""

from __future__ import annotations


def normalize_string_list(value: list | None, *, limit: int = 24) -> list[str]:
    if not value:
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out[:limit]


def normalize_color_palette(value: dict | None) -> dict[str, str]:
    if not value:
        return {}
    allowed = ("primary", "secondary", "accent", "background", "text")
    out: dict[str, str] = {}
    for key in allowed:
        raw = value.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            out[key] = text
    return out
