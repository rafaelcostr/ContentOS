"""Format specialist profile for prompt injection."""

from __future__ import annotations

from contentos_intelligence.domain.specialist import SpecialistProfile, SpecialistSelection


def format_specialist_context(profile: SpecialistProfile) -> str:
    parts = [f"Especialista: {profile.name} (nicho {profile.niche})"]
    if profile.tone:
        parts.append(f"Tom: {profile.tone}")
    if profile.structure:
        parts.append(f"Estrutura: {profile.structure}")
    if profile.vocabulary:
        parts.append(f"Vocabulário: {', '.join(profile.vocabulary[:10])}")
    if profile.cta_style:
        parts.append(f"CTA sugerido: {profile.cta_style}")
    return ". ".join(parts) + "."


def apply_specialist_to_payload(payload: dict, selection: SpecialistSelection) -> dict:
    updated = dict(payload)
    profile = selection.specialist
    updated["specialist_selection"] = selection.to_dict()
    updated["specialist_id"] = profile.specialist_id
    updated["specialist_context"] = format_specialist_context(profile)
    updated["specialist_prompt_pack"] = profile.prompt_pack
    if not updated.get("niche"):
        updated["niche"] = profile.niche
    return updated
