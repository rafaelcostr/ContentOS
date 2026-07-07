"""Project DNA 2.0 helpers — V5.1.4 (cinematic, content angle, brand)."""

from __future__ import annotations

VALID_CINEMATIC_PRESETS = frozenset({"default", "dynamic", "calm", "punchy"})

VALID_CONTENT_ANGLES = frozenset({
    "hype",
    "documentary",
    "tutorial",
    "news",
    "storytelling",
    "calm",
})

CONTENT_ANGLE_PACE: dict[str, str] = {
    "hype": "fast",
    "documentary": "slow",
    "tutorial": "medium",
    "news": "fast",
    "storytelling": "medium",
    "calm": "slow",
}

CONTENT_ANGLE_MOVEMENT: dict[str, str] = {
    "hype": "speed-ramp-up",
    "documentary": "ken-burns",
    "tutorial": "static",
    "news": "static",
    "storytelling": "zoom-in",
    "calm": "zoom-in",
}

CONTENT_ANGLE_LABELS: dict[str, str] = {
    "hype": "hype / energético",
    "documentary": "documentário",
    "tutorial": "tutorial",
    "news": "notícia",
    "storytelling": "storytelling",
    "calm": "calmo",
}


def normalize_cinematic_preset(value: str | None) -> str:
    if not value:
        return ""
    preset = str(value).strip().lower()
    return preset if preset in VALID_CINEMATIC_PRESETS else ""


def normalize_content_angle(value: str | None) -> str:
    if not value:
        return ""
    angle = str(value).strip().lower().replace("_", "-")
    return angle if angle in VALID_CONTENT_ANGLES else ""


def normalize_brand_keywords(value: list | None) -> list[str]:
    if not value:
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out[:24]
