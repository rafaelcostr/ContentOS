"""Verify Pexels/Pixabay content sources are configured and reachable."""

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
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    pixabay_key = os.getenv("PIXABAY_API_KEY", "").strip()

    print("Content sources configuration")
    print(f"  CONTENT_SOURCES_ENABLED: {', '.join(enabled) or '(empty — using package default)'}")
    print(f"  PEXELS_API_KEY: {'set' if pexels_key else 'MISSING'}")
    print(f"  PIXABAY_API_KEY: {'set' if pixabay_key else 'MISSING'}")

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
        if row["source_id"] in {"pexels", "pixabay"} and not row.get("healthy"):
            ok = False

    if "pexels" in sources and not pexels_key:
        print("\nWARN: pexels enabled but PEXELS_API_KEY is empty", file=sys.stderr)
        ok = False
    if "pixabay" in sources and not pixabay_key:
        print("\nWARN: pixabay enabled but PIXABAY_API_KEY is empty", file=sys.stderr)
        ok = False

    if ok:
        print("\nContent sources ready for factory-full media acquisition.")
        return 0

    print(
        "\nAdd API keys to .env (free tiers: pexels.com/api, pixabay.com/api/docs)\n"
        "  CONTENT_SOURCES_ENABLED=pexels,pixabay,local_library,own_library\n"
        "  PEXELS_API_KEY=...\n"
        "  PIXABAY_API_KEY=...\n"
        "Then: docker compose -f docker/docker-compose.yml up -d --build agents-worker gateway",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
