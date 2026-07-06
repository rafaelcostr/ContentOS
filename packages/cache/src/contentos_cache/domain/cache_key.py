"""Cache key generation."""

from __future__ import annotations

import hashlib


def build_cache_key(
    *,
    agent: str,
    topic: str,
    prompt_version: str,
    model: str,
    memory_context: str = "",
) -> str:
    """Deterministic cache key: hash(agent + topic + prompt_version + model + memory)."""
    normalized = "|".join(
        [
            agent.strip().lower(),
            topic.strip().lower(),
            prompt_version.strip(),
            model.strip(),
            memory_context.strip(),
        ]
    )
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    return f"contentos:cache:{agent}:{digest}"


def agent_from_key(key: str) -> str | None:
    parts = key.split(":")
    if len(parts) >= 3 and parts[0] == "contentos" and parts[1] == "cache":
        return parts[2]
    return None


def agent_key_pattern(agent: str) -> str:
    return f"contentos:cache:{agent}:*"
