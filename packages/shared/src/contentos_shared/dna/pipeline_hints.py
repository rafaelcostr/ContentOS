"""Project DNA 2.0 → pipeline payload hints (V5.1.4)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from contentos_memory.domain.dna_v2 import normalize_cinematic_preset
from contentos_memory.domain.project_memory import ProjectMemoryData
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_shared.cinematic.editor import CINEMATIC_PRESETS


def build_cinematic_from_memory(memory: ProjectMemoryData) -> dict[str, Any] | None:
    preset = normalize_cinematic_preset(memory.cinematic_preset) or "default"
    prefs = dict(memory.editing_preferences or {})
    if not memory.cinematic_preset and not prefs:
        return None
    cinematic = dict(CINEMATIC_PRESETS.get(preset, CINEMATIC_PRESETS["default"]))
    cinematic["preset"] = preset
    for key in (
        "enable_zoom",
        "enable_ducking",
        "enable_speed_ramp",
        "music_volume",
        "ducking_ratio",
        "ducking_threshold",
        "fade_duration",
    ):
        if key in prefs and prefs[key] is not None:
            cinematic[key] = prefs[key]
    return cinematic


def project_dna_payload_hints(memory: ProjectMemoryData) -> dict[str, Any]:
    """Merge voice/cinematic/angle hints for workflow payload injection."""
    hints: dict[str, Any] = {}
    cinematic = build_cinematic_from_memory(memory)
    if cinematic:
        hints["cinematic"] = cinematic

    dna_block: dict[str, Any] = {}
    if memory.content_angle:
        dna_block["content_angle"] = memory.content_angle
    if memory.cinematic_preset:
        dna_block["cinematic_preset"] = memory.cinematic_preset
    if memory.brand_keywords:
        dna_block["brand_keywords"] = list(memory.brand_keywords)
    if dna_block:
        hints["project_dna"] = dna_block

    if memory.brand_keywords:
        hints["brand_keywords"] = list(memory.brand_keywords)
    if memory.content_angle:
        hints["content_angle"] = memory.content_angle
    return hints


async def project_dna_payload_hints_async(
    session: AsyncSession,
    project_id: UUID,
) -> dict[str, Any]:
    from contentos_memory.infrastructure.db_repository import MemoryRepository

    memory = await MemoryRepository().get(session, project_id)
    return project_dna_payload_hints(memory)
