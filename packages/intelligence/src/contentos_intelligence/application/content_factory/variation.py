"""Batch variation planner — hook/angle rotation (V5.3.2)."""

from __future__ import annotations

from contentos_memory.domain.dna_v2 import CONTENT_ANGLE_LABELS, VALID_CONTENT_ANGLES

from contentos_intelligence.domain.content_batch import BatchVariant

DEFAULT_ANGLE_ORDER: tuple[str, ...] = (
    "hype",
    "documentary",
    "tutorial",
    "news",
    "storytelling",
    "calm",
)

HOOK_TEMPLATES: dict[str, tuple[str, ...]] = {
    "hype": (
        "Você PRECISA ver isso sobre {topic}",
        "Ninguém está falando de {topic} assim",
        "Isso sobre {topic} vai explodir",
    ),
    "documentary": (
        "A história real por trás de {topic}",
        "O que ninguém te contou sobre {topic}",
        "{topic}: os fatos que importam",
    ),
    "tutorial": (
        "Como dominar {topic} em poucos passos",
        "Guia rápido: {topic} explicado",
        "Aprenda {topic} do jeito certo",
    ),
    "news": (
        "Últimas novidades de {topic}",
        "Breaking: {topic} acaba de mudar",
        "O que mudou em {topic} agora",
    ),
    "storytelling": (
        "A jornada surpreendente de {topic}",
        "Era uma vez {topic}…",
        "A história de {topic} que prende do início ao fim",
    ),
    "calm": (
        "Tudo sobre {topic}, com calma",
        "Entenda {topic} sem pressa",
        "{topic} explicado de forma simples",
    ),
}


def _normalize_angles(angles: list[str] | None) -> list[str]:
    if not angles:
        return list(DEFAULT_ANGLE_ORDER)
    out: list[str] = []
    for raw in angles:
        angle = str(raw).strip().lower().replace("_", "-")
        if angle in VALID_CONTENT_ANGLES and angle not in out:
            out.append(angle)
    return out or list(DEFAULT_ANGLE_ORDER)


def hook_hint_for_angle(topic: str, angle: str, index: int) -> str:
    templates = HOOK_TEMPLATES.get(angle) or HOOK_TEMPLATES["hype"]
    template = templates[index % len(templates)]
    return template.format(topic=topic.strip() or "o tema")


def plan_variations(
    topic: str,
    quantity: int,
    *,
    angles: list[str] | None = None,
    topic_suffix: bool = True,
) -> list[BatchVariant]:
    """Build N variants rotating content_angle and hook templates."""
    count = max(1, min(int(quantity), 24))
    base_topic = (topic or "").strip() or "Tema"
    rotation = _normalize_angles(angles)
    variants: list[BatchVariant] = []
    for i in range(count):
        angle = rotation[i % len(rotation)]
        label = CONTENT_ANGLE_LABELS.get(angle, angle)
        variant_topic = base_topic
        if topic_suffix and count > 1:
            variant_topic = f"{base_topic} — {label} #{i + 1}"
        variants.append(
            BatchVariant(
                index=i,
                topic=variant_topic,
                content_angle=angle,
                hook_hint=hook_hint_for_angle(base_topic, angle, i),
            )
        )
    return variants
