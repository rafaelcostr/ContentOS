"""Helpers for normalizing LLM JSON payloads between pipeline steps."""


def coerce_dict(value: object, *, string_key: str = "title") -> dict:
    """Ensure payload fragments are dicts — Ollama sometimes returns plain strings."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        return {string_key: value.strip()}
    return {}


def normalize_research_output(data: dict) -> dict:
    """Normalize research agent output for downstream script/scene handlers."""
    out = dict(data)
    selected = out.get("selected_topic")
    if isinstance(selected, str):
        out["selected_topic"] = {"title": selected.strip(), "angle": "", "hook": "", "why_viral": ""}
    elif not isinstance(selected, dict):
        topics = out.get("topics") or []
        first = topics[0] if topics and isinstance(topics[0], dict) else None
        out["selected_topic"] = first or {"title": out.get("topic", ""), "angle": "", "hook": ""}

    topics = out.get("topics")
    if isinstance(topics, list):
        normalized: list = []
        for item in topics:
            if isinstance(item, dict):
                normalized.append(item)
            elif isinstance(item, str) and item.strip():
                normalized.append({"title": item.strip(), "angle": "", "hook": ""})
        out["topics"] = normalized

    return out
