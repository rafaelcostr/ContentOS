"""Build and register content source adapters."""

from __future__ import annotations

import os

from contentos_sources.adapters.custom import CustomSource
from contentos_sources.adapters.gameplay import GameplaySource
from contentos_sources.adapters.licensed_trailers import LicensedTrailerSource
from contentos_sources.adapters.local_library import LocalLibrarySource
from contentos_sources.adapters.own_library import OwnLibrarySource
from contentos_sources.adapters.pexels import PexelsSource
from contentos_sources.adapters.pixabay import PixabaySource
from contentos_sources.adapters.rss import RSSSource
from contentos_sources.infrastructure.registry import SourceRegistry


def build_registry() -> SourceRegistry:
    registry = SourceRegistry()
    registry.register(LocalLibrarySource())
    registry.register(OwnLibrarySource())
    registry.register(PexelsSource())
    registry.register(PixabaySource())
    registry.register(RSSSource())
    registry.register(GameplaySource())
    registry.register(LicensedTrailerSource())
    registry.register(CustomSource())
    return registry


def enabled_source_ids() -> list[str]:
    raw = os.getenv("CONTENT_SOURCES_ENABLED", "local_library,own_library")
    return [s.strip() for s in raw.split(",") if s.strip()]
