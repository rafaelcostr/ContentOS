"""Pilot specialist profiles — Epic 5 (Gaming, Technology, Business)."""

from __future__ import annotations

from contentos_intelligence.domain.specialist import SpecialistProfile

PILOT_SPECIALISTS: dict[str, SpecialistProfile] = {
    "gaming": SpecialistProfile(
        specialist_id="gaming",
        name="Gaming Specialist",
        niche="gaming",
        tone="energético, direto, linguagem de comunidade gamer",
        vocabulary=["gameplay", "meta", "buff", "nerf", "speedrun", "easter egg", "patch", "rank"],
        cta_style="Comenta seu main e segue para mais dicas de jogo",
        structure="hook chocante → contexto rápido → revelação → CTA comunidade",
        prompt_pack="gaming_v1",
        metadata={"pilot": True, "tier": "v4.1.3"},
    ),
    "technology": SpecialistProfile(
        specialist_id="technology",
        name="Technology Specialist",
        niche="technology",
        tone="claro, informativo, sem hype vazio",
        vocabulary=["IA", "software", "hardware", "update", "review", "tutorial", "API", "chip"],
        cta_style="Salva para não perder e segue para mais tech",
        structure="problema → explicação simples → insight prático → CTA",
        prompt_pack="technology_v1",
        metadata={"pilot": True, "tier": "v4.1.3"},
    ),
    "business": SpecialistProfile(
        specialist_id="business",
        name="Business Specialist",
        niche="business",
        tone="autoridade acessível, foco em resultado",
        vocabulary=["ROI", "funil", "vendas", "marca", "estratégia", "lucro", "cliente", "growth"],
        cta_style="Comenta como você aplicaria isso no seu negócio",
        structure="dor do mercado → framework rápido → prova social → CTA",
        prompt_pack="business_v1",
        metadata={"pilot": True, "tier": "v4.1.3"},
    ),
    "general": SpecialistProfile(
        specialist_id="general",
        name="General Creator",
        niche="general",
        tone="versátil, conversacional",
        vocabulary=[],
        cta_style="Segue para mais conteúdo assim",
        structure="gancho → desenvolvimento → CTA",
        prompt_pack="general_v1",
        metadata={"pilot": False, "default": True},
    ),
}

# Roadmap: 8 additional niches (not enabled in V4.1.3 pilot)
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


def list_specialists(*, include_upcoming: bool = False) -> list[SpecialistProfile]:
    profiles = list(PILOT_SPECIALISTS.values())
    if include_upcoming:
        for sid in UPCOMING_SPECIALIST_IDS:
            profiles.append(
                SpecialistProfile(
                    specialist_id=sid,
                    name=f"{sid.title()} Specialist",
                    niche=sid,
                    metadata={"pilot": False, "enabled": False, "coming_soon": True},
                )
            )
    return profiles


def get_specialist(specialist_id: str) -> SpecialistProfile | None:
    return PILOT_SPECIALISTS.get(specialist_id)
