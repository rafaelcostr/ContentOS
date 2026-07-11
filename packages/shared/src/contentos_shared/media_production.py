"""Production media and render policy flags (shared by agents)."""



from __future__ import annotations

import os
from typing import Any


def is_production_env() -> bool:

    value = os.getenv("APP_ENV") or os.getenv("ENV") or os.getenv("ENVIRONMENT")

    return str(value or "").strip().lower() in {"prod", "production", "release"}





def require_media_assets() -> bool:

    raw = os.getenv("MEDIA_REQUIRE_ASSETS")

    if raw is not None:

        return raw.strip().lower() in {"1", "true", "yes", "on"}

    return is_production_env()





def require_clip_coverage() -> bool:

    """When true, takes must cover every scene with real media."""

    raw = os.getenv("MEDIA_REQUIRE_CLIPS") or os.getenv("MEDIA_REQUIRE_ASSETS")

    if raw is not None:

        return raw.strip().lower() in {"1", "true", "yes", "on"}

    return is_production_env()





def render_allow_placeholder() -> bool:

    """When false, editor/takes/ffmpeg must fail instead of rendering placeholder clips."""

    raw = os.getenv("RENDER_ALLOW_PLACEHOLDER")

    if raw is not None:

        return raw.strip().lower() in {"1", "true", "yes", "on"}

    return not is_production_env()





def is_placeholder_asset_key(asset_key: str | None) -> bool:

    if not asset_key:

        return True

    normalized = asset_key.replace("\\", "/").lower()

    filename = normalized.rsplit("/", 1)[-1]

    return filename.startswith("placeholder") or "placeholder_" in normalized





def scene_clip_coverage(labels: list[str], clips: list[dict[str, Any]]) -> dict[str, Any]:

    covered = {

        str(clip.get("label"))

        for clip in clips

        if clip.get("asset_key") and not is_placeholder_asset_key(str(clip.get("asset_key")))

    }

    missing = [label for label in labels if label not in covered]

    return {

        "expected_scene_count": len(labels),

        "covered_scene_count": len(labels) - len(missing),

        "missing_scene_labels": missing,

        "passed": not missing,

    }


