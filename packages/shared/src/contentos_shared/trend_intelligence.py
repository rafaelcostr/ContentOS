"""Trend Intelligence — aggregate memory + analytics into research patterns (V3 Tier B9)."""

from __future__ import annotations

from typing import Any

from contentos_shared.payload_utils import coerce_dict

_DEFAULT_PATTERNS = [
    "Gancho forte nos primeiros 3 segundos",
    "Pergunta retórica ou afirmação chocante no início",
    "Ritmo rápido com nova informação a cada 3–5 segundos",
    "CTA claro no final (curtir, comentar, seguir)",
    "Linguagem coloquial brasileira",
]

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "game": ["gameplay", "lançamento", "rumores", "easter egg", "comparação"],
    "tech": ["novidade", "review", "vale a pena", "vs", "tutorial rápido"],
    "news": ["breaking", "o que ninguém viu", "impacto", "timeline"],
}


def _as_str_list(value: Any, *, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _memory_dict(memory: Any) -> dict:
    if memory is None:
        return {}
    if hasattr(memory, "to_dict"):
        return coerce_dict(memory.to_dict())
    return coerce_dict(memory)


def _score(insight: dict) -> float:
    analysis = coerce_dict(insight.get("analysis"))
    for key in ("score", "overall", "performance_score"):
        try:
            return float(analysis.get(key) or insight.get(key) or 0)
        except (TypeError, ValueError):
            continue
    return 0.0


def _topic_keywords(topic: str, niche: str) -> list[str]:
    text = f"{topic} {niche}".lower()
    if any(w in text for w in ("jogo", "gta", "game", "playstation", "xbox", "nintendo")):
        return _TOPIC_KEYWORDS["game"]
    if any(w in text for w in ("iphone", "android", "tech", " ia", "app", "software")):
        return _TOPIC_KEYWORDS["tech"]
    if any(w in text for w in ("notícia", "noticia", "política", "mundo", "brasil")):
        return _TOPIC_KEYWORDS["news"]
    return []


def _patterns_from_memory(memory: dict) -> tuple[list[str], list[str], list[str]]:
    patterns: list[str] = []
    hooks: list[str] = []
    avoid: list[str] = []

    if memory.get("hook_style"):
        hooks.append(str(memory["hook_style"]))
        patterns.append(f"Estilo de gancho preferido: {memory['hook_style']}")
    if memory.get("tone"):
        patterns.append(f"Tom de voz: {memory['tone']}")
    if memory.get("goal"):
        patterns.append(f"Objetivo do canal: {memory['goal']}")
    if memory.get("cta"):
        patterns.append(f"CTA recorrente: {memory['cta']}")
    if memory.get("avg_duration"):
        patterns.append(f"Duração alvo: {int(float(memory['avg_duration']))}s")

    vocab = _as_str_list(memory.get("vocabulary"), limit=10)
    if vocab:
        patterns.append(f"Vocabulário do projeto: {', '.join(vocab)}")

    for entry in _as_str_list(
        [h.get("summary") for h in (memory.get("history") or []) if isinstance(h, dict)],
        limit=3,
    ):
        if entry:
            patterns.append(f"Aprendizado recente: {entry}")

    style = coerce_dict(memory.get("style"))
    for key, value in list(style.items())[:4]:
        patterns.append(f"{key}: {value}")

    return patterns, hooks, avoid


def _patterns_from_insights(insights: list[dict]) -> tuple[list[str], list[str], list[str]]:
    patterns: list[str] = []
    hooks: list[str] = []
    avoid: list[str] = []

    ranked = sorted(insights, key=_score, reverse=True)
    top = [i for i in ranked if _score(i) >= 60][:5]
    weak = [i for i in ranked if 0 < _score(i) < 50][:3]

    for ins in top:
        analysis = coerce_dict(ins.get("analysis"))
        metrics = coerce_dict(ins.get("metrics"))
        title = metrics.get("title") or analysis.get("title")
        if title:
            patterns.append(f"Vídeo bem-sucedido: {title}")
        for strength in _as_str_list(analysis.get("strengths"), limit=2):
            patterns.append(f"Força comprovada: {strength}")
        for suggestion in _as_str_list(analysis.get("suggestions"), limit=2):
            patterns.append(f"Sugestão validada: {suggestion}")
        for tweak in analysis.get("recommended_prompt_tweaks") or []:
            if isinstance(tweak, dict):
                for key, value in tweak.items():
                    if key in ("hook_style", "hook", "gancho"):
                        hooks.append(str(value))
                    else:
                        patterns.append(f"Ajuste recomendado ({key}): {value}")

    for ins in weak:
        analysis = coerce_dict(ins.get("analysis"))
        for weakness in _as_str_list(analysis.get("weaknesses"), limit=2):
            avoid.append(weakness)

    return patterns, hooks, avoid


def _pacing_hint(insights: list[dict], memory: dict) -> str:
    scores = [_score(i) for i in insights if _score(i) > 0]
    if scores and sum(scores) / len(scores) >= 75:
        return "rápido"
    if memory.get("hook_style") and "choque" in str(memory["hook_style"]).lower():
        return "rápido"
    if scores and sum(scores) / len(scores) <= 50:
        return "moderado"
    return "dinâmico"


def build_trend_brief(
    *,
    topic: str,
    niche: str = "",
    memory: Any = None,
    insights: list[dict] | None = None,
) -> dict:
    """Build structured trend brief from project memory and analytics history."""
    mem = _memory_dict(memory)
    insight_rows = insights or []
    niche = niche or str(mem.get("niche") or "")

    mem_patterns, mem_hooks, mem_avoid = _patterns_from_memory(mem)
    ins_patterns, ins_hooks, ins_avoid = _patterns_from_insights(insight_rows)

    patterns = _dedupe(mem_patterns + ins_patterns)
    hooks = _dedupe(mem_hooks + ins_hooks)
    avoid = _dedupe(mem_avoid + ins_avoid)

    keywords = _topic_keywords(topic, niche)
    if keywords:
        patterns.append(f"Ângulos quentes para o nicho: {', '.join(keywords)}")

    sources: list[str] = []
    if mem_patterns:
        sources.append("memory")
    if ins_patterns:
        sources.append("analytics")
    if not patterns:
        patterns = list(_DEFAULT_PATTERNS)
        sources.append("default")

    if not hooks:
        hooks = ["curiosidade", "choque", "pergunta"]

    return {
        "topic": topic,
        "niche": niche,
        "patterns": patterns[:12],
        "recommended_hooks": hooks[:6],
        "avoid": avoid[:6],
        "keywords": keywords[:8],
        "pacing_hint": _pacing_hint(insight_rows, mem),
        "insight_count": len(insight_rows),
        "sources": sources,
    }


def format_trend_context(brief: dict) -> str:
    """Compact string for {{trend_context}} in the research prompt."""
    parts: list[str] = []
    if brief.get("pacing_hint"):
        parts.append(f"Ritmo sugerido: {brief['pacing_hint']}")
    if brief.get("keywords"):
        parts.append(f"Palavras-chave: {', '.join(brief['keywords'])}")
    if brief.get("patterns"):
        parts.append("Padrões virais: " + "; ".join(brief["patterns"][:8]))
    if brief.get("recommended_hooks"):
        parts.append("Ganchos recomendados: " + ", ".join(brief["recommended_hooks"][:5]))
    if brief.get("avoid"):
        parts.append("Evitar: " + "; ".join(brief["avoid"][:4]))
    if brief.get("sources"):
        parts.append(f"Fontes: {', '.join(brief['sources'])}")
    return ". ".join(parts) + ("." if parts else "")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out
