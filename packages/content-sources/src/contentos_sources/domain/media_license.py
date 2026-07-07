"""Media license types and validation for content sources (V5.0)."""

from __future__ import annotations

import os

ROYALTY_FREE = "royalty_free"
CREATIVE_COMMONS = "creative_commons"
PREVIEW_ONLY = "preview_only"
UNKNOWN = "unknown"

DEFAULT_ALLOWED = frozenset({ROYALTY_FREE, CREATIVE_COMMONS})


def allowed_licenses() -> frozenset[str]:
    raw = os.getenv("MEDIA_ALLOWED_LICENSES", "royalty_free,creative_commons")
    values = {part.strip() for part in raw.split(",") if part.strip()}
    return values or set(DEFAULT_ALLOWED)


def is_license_allowed(license_type: str | None) -> bool:
    if not license_type:
        return False
    return license_type in allowed_licenses()


def max_download_bytes() -> int:
    mb = float(os.getenv("MEDIA_MAX_DOWNLOAD_MB", "50"))
    return int(mb * 1024 * 1024)
