"""Niche-based specialist selector — Epic 5 pilot."""

from __future__ import annotations

from contentos_intelligence.application.specialists.catalog import PILOT_SPECIALISTS, get_specialist
from contentos_intelligence.application.specialists.signals import NICHE_ALIASES, NICHE_KEYWORDS
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.specialist import SpecialistProfile, SpecialistSelection


def _normalize_niche(value: str) -> str:
    key = (value or "").strip().lower()
    return NICHE_ALIASES.get(key, key)


def _collect_text(context: IntelligenceContext) -> str:
    payload = context.payload or {}
    parts = [str(context.topic or "")]
    for key in ("niche", "topic", "specialist_id"):
        if payload.get(key):
            parts.append(str(payload[key]))
    memory = payload.get("project_memory") or payload.get("memory") or {}
    if isinstance(memory, dict) and memory.get("niche"):
        parts.append(str(memory["niche"]))
    dna = payload.get("dna_context") or payload.get("project_dna") or {}
    if isinstance(dna, dict):
        for key in ("niche", "goal", "tone"):
            if dna.get(key):
                parts.append(str(dna[key]))
    script = payload.get("script") or {}
    if isinstance(script, dict):
        for key in ("title", "hook", "full_text"):
            val = script.get(key)
            if val:
                parts.append(str(val)[:300])
    return " ".join(parts).lower()


def _score_profile(profile: SpecialistProfile, text: str, niche_hint: str) -> tuple[float, list[str]]:
    if profile.specialist_id == "general":
        return 0.0, []

    reasons: list[str] = []
    score = 0.0
    normalized_hint = _normalize_niche(niche_hint)
    if normalized_hint and normalized_hint == profile.specialist_id:
        score += 40.0
        reasons.append(f"niche_hint={normalized_hint}")

    keywords = NICHE_KEYWORDS.get(profile.specialist_id, ())
    for kw in keywords:
        if kw in text:
            score += 8.0
            reasons.append(f"keyword:{kw}")

    for vocab in profile.vocabulary:
        if vocab.lower() in text:
            score += 4.0
            reasons.append(f"vocab:{vocab}")

    if payload_id := profile.specialist_id:
        if payload_id in text:
            score += 6.0
            reasons.append(f"id:{payload_id}")

    return score, reasons


class NicheSpecialistSelector:
    """Select gaming / technology / business specialist from topic + project signals."""

    async def select(self, context: IntelligenceContext) -> SpecialistSelection:
        payload = context.payload or {}
        niche_hint = str(payload.get("niche") or "")
        memory = payload.get("project_memory") or payload.get("memory") or {}
        if isinstance(memory, dict) and memory.get("niche"):
            niche_hint = niche_hint or str(memory["niche"])
        if payload.get("specialist_id"):
            forced = get_specialist(str(payload["specialist_id"]))
            if forced:
                return SpecialistSelection(
                    specialist=forced,
                    confidence=1.0,
                    reason="forced_specialist_id",
                )

        text = _collect_text(context)
        niche_hint = niche_hint or text[:80]
        best_id = "general"
        best_score = 0.0
        best_reasons: list[str] = []

        for sid in ("gaming", "technology", "business"):
            profile = PILOT_SPECIALISTS[sid]
            score, reasons = _score_profile(profile, text, niche_hint)
            if score > best_score:
                best_score = score
                best_id = sid
                best_reasons = reasons

        if best_score < 12.0:
            profile = PILOT_SPECIALISTS["general"]
            return SpecialistSelection(
                specialist=profile,
                confidence=0.35,
                reason="low_signal_default_general",
            )

        profile = PILOT_SPECIALISTS[best_id]
        confidence = min(0.98, 0.45 + best_score / 100.0)
        reason = ", ".join(best_reasons[:5]) or f"matched_{best_id}"
        return SpecialistSelection(specialist=profile, confidence=confidence, reason=reason)
