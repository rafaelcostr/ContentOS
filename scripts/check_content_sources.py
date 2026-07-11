"""Verify local content sources (library) are configured and reachable.

External download (Pexels/Pixabay) was moved to Media Collector.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


def _load_dotenv() -> None:
    """Load project .env into os.environ (only unset keys)."""
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        existing = os.environ.get(key, "")
        if key not in os.environ or not str(existing).strip():
            os.environ[key] = value


async def main() -> int:
    _load_dotenv()
    enabled = [s.strip() for s in os.getenv("CONTENT_SOURCES_ENABLED", "").split(",") if s.strip()]

    print("Content sources configuration (local library only)")
    print(f"  CONTENT_SOURCES_ENABLED: {', '.join(enabled) or '(empty — using package default)'}")

    remote = [s for s in enabled if s in {"pexels", "pixabay"}]
    if remote:
        print(
            f"\nWARN: remote sources {remote} are no longer supported in ContentOS. "
            "Use Media Collector and set CONTENT_SOURCES_ENABLED=local_library,own_library",
            file=sys.stderr,
        )

    try:
        from contentos_sources import get_source_manager
    except ImportError:
        print("\nFAIL: contentos_sources package not installed", file=sys.stderr)
        return 1

    mgr = get_source_manager()
    sources = mgr.list_sources()
    print(f"\nEnabled in worker: {', '.join(sources) or '(none)'}")

    rows = await mgr.health_all()
    ok = True
    for row in rows:
        icon = "OK" if row.get("healthy") else "FAIL"
        print(f"  {icon} {row['source_id']}: {row.get('message', '')}")
        if not row.get("healthy") and row["source_id"] in {"local_library", "own_library"}:
            ok = False

    if not any(s in sources for s in ("local_library", "own_library")):
        print("\nWARN: no local library sources enabled", file=sys.stderr)
        ok = False

    if ok:
        print(
            "\nLocal sources ready. Media Collector should upload via "
            "POST /api/v1/assets/takes/upload"
        )
        return 0

    print(
        "\nSet in .env:\n"
        "  CONTENT_SOURCES_ENABLED=local_library,own_library\n"
        "External download is owned by Media Collector.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
