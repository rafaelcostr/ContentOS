"""A/B variant generation heuristics — Epic 6."""

from __future__ import annotations

from contentos_intelligence.domain.ab_testing import AbVariant, new_variant_id


def _unique_strings(items: list[str], limit: int = 3) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _pad_variants(base: str, mutations: list[str], *, limit: int = 3) -> list[str]:
    candidates = _unique_strings([base, *mutations], limit=limit)
    idx = 0
    while len(candidates) < limit and base:
        suffix = ["", " — você precisa ver isso", " (urgente)"][idx % 3]
        candidate = f"{base}{suffix}".strip()
        if candidate not in candidates:
            candidates.append(candidate)
        idx += 1
    return candidates[:limit]


def generate_hook_variants(payload: dict) -> list[AbVariant]:
    hook = payload.get("selected_hook") or payload.get("hook") or {}
    if not isinstance(hook, dict):
        hook = {}
    base = str(payload.get("hook_text") or hook.get("hook_text") or hook.get("hook") or "").strip()
    topic = str(payload.get("topic") or "")
    if not base and topic:
        base = f"Você não vai acreditar em {topic}."
    alts = []
    for alt in hook.get("alternatives") or []:
        if isinstance(alt, dict):
            alts.append(str(alt.get("hook_text") or alt.get("hook") or ""))
    texts = _pad_variants(
        base,
        alts + [f"Para tudo: {base}", f"Ninguém fala sobre isso em {topic}"],
    )
    return [AbVariant(variant_id=new_variant_id(), value=t) for t in texts]


def generate_title_variants(payload: dict) -> list[AbVariant]:
    script = payload.get("script") or {}
    if not isinstance(script, dict):
        script = {}
    base = str(script.get("title") or payload.get("topic") or "").strip()
    texts = _pad_variants(
        base,
        [
            f"{base} — a verdade",
            f"O segredo de {base}",
            f"{base} em 60 segundos",
        ],
    )
    return [AbVariant(variant_id=new_variant_id(), value=t) for t in texts]


def generate_cta_variants(payload: dict) -> list[AbVariant]:
    script = payload.get("script") or {}
    if not isinstance(script, dict):
        script = {}
    base = str(script.get("call_to_action") or script.get("cta") or "").strip()
    texts = _pad_variants(
        base or "Siga para mais conteúdo assim.",
        [
            "Comenta aí o que você achou!",
            "Salva esse vídeo e compartilha com um amigo.",
            "Ativa o sininho — tem mais vindo aí.",
        ],
    )
    return [AbVariant(variant_id=new_variant_id(), value=t) for t in texts]


def generate_thumbnail_variants(payload: dict) -> list[AbVariant]:
    """Text concepts for thumbnail — image generation stays in thumbnail step."""
    script = payload.get("script") or {}
    title = ""
    if isinstance(script, dict):
        title = str(script.get("title") or "")
    topic = str(payload.get("topic") or title or "viral")
    concepts = _pad_variants(
        f"{topic} | CHOCANTE",
        [
            f"⚠️ {topic}",
            f"{topic} — EXPOSTO",
            f"Você viu isso? {topic}",
        ],
    )
    return [
        AbVariant(variant_id=new_variant_id(), value=c, metadata={"type": "thumbnail_concept"})
        for c in concepts
    ]


def generate_opener_variants(payload: dict) -> list[AbVariant]:
    script = payload.get("script") or {}
    hook = payload.get("selected_hook") or payload.get("hook") or {}
    if not isinstance(script, dict):
        script = {}
    if not isinstance(hook, dict):
        hook = {}
    full = str(script.get("full_text") or script.get("hook") or "")
    hook_text = str(payload.get("hook_text") or hook.get("hook_text") or "")
    base = hook_text or (full.split(".")[0] if full else "")
    texts = _pad_variants(
        base,
        [
            full[:80] if full else base,
            f"{hook_text} — e isso muda tudo.",
            f"Antes de rolar: {hook_text or topic_line(payload)}",
        ],
    )
    return [AbVariant(variant_id=new_variant_id(), value=t) for t in texts]


def topic_line(payload: dict) -> str:
    return str(payload.get("topic") or "esse assunto")


GENERATORS = {
    "hook": generate_hook_variants,
    "title": generate_title_variants,
    "cta": generate_cta_variants,
    "thumbnail": generate_thumbnail_variants,
    "opener": generate_opener_variants,
}
