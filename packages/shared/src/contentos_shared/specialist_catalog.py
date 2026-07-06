"""Shared specialist metadata for agent catalog and API — V4.1.3 pilot."""

from __future__ import annotations

SPECIALIST_CATALOG: list[dict[str, str | bool]] = [
    {
        "specialist_id": "gaming",
        "name": "Gaming Specialist",
        "niche": "gaming",
        "prompt_pack": "gaming_v1",
        "pilot": True,
        "enabled": True,
    },
    {
        "specialist_id": "technology",
        "name": "Technology Specialist",
        "niche": "technology",
        "prompt_pack": "technology_v1",
        "pilot": True,
        "enabled": True,
    },
    {
        "specialist_id": "business",
        "name": "Business Specialist",
        "niche": "business",
        "prompt_pack": "business_v1",
        "pilot": True,
        "enabled": True,
    },
    {
        "specialist_id": "general",
        "name": "General Creator",
        "niche": "general",
        "prompt_pack": "general_v1",
        "pilot": False,
        "enabled": True,
    },
]

UPCOMING_SPECIALIST_IDS = (
    "fitness",
    "finance",
    "education",
    "entertainment",
    "lifestyle",
    "news",
    "sports",
    "food",
)

CREATIVE_AGENT_SPECIALIST_SUITES = ("gaming", "technology", "business", "general")
