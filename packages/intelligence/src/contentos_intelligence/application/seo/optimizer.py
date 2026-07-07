"""SEO optimizer — titles, hashtags, descriptions (V5.2.3)."""

from __future__ import annotations

import os
import re
from typing import Any

from contentos_shared.payload_utils import coerce_dict

from contentos_intelligence.domain.seo_package import PlatformSeo, SeoPackage

_PLATFORMS = ("tiktok", "youtube_shorts", "instagram_reels")
_PLATFORM_HASHTAGS: dict[str, list[str]] = {
    "tiktok": ["fyp", "viral", "foryou"],
    "youtube_shorts": ["shorts", "youtube", "viral"],
    "instagram_reels": ["reels", "instagram", "viral"],
}
_STOPWORDS = frozenset(
    "a o e de da do das dos em no na nos nas um uma para com por que como".split()
)


def seo_engine_enabled() -> bool:
    return os.getenv("SEO_ENGINE_ENABLED", "true").lower() in ("1", "true", "yes")


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _truncate(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", text) if len(w) > 2]


def _unique_tags(*groups: list[str], limit: int = 10) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for raw in group:
            tag = re.sub(r"[^a-zA-Z0-9À-ÿ_]", "", str(raw).lower().lstrip("#"))
            if not tag or tag in seen or tag in _STOPWORDS:
                continue
            seen.add(tag)
            out.append(tag)
            if len(out) >= limit:
                return out
    return out


def _script_context(payload: dict) -> dict[str, str]:
    script = coerce_dict(payload.get("script"))
    hook_block = coerce_dict(payload.get("selected_hook"))
    topic = str(
        script.get("title")
        or hook_block.get("hook_text")
        or coerce_dict(payload.get("selected_topic")).get("title")
        or payload.get("topic")
        or ""
    ).strip()
    hook = str(
        hook_block.get("hook_text")
        or script.get("hook")
        or script.get("opening")
        or ""
    ).strip()
    body = str(
        script.get("full_text")
        or " ".join(
            str(script.get(k) or "")
            for k in ("development", "curiosity", "body")
        )
        or ""
    ).strip()
    cta = str(script.get("call_to_action") or script.get("cta") or "").strip()
    return {"topic": topic, "hook": hook, "body": body, "cta": cta}


def _brand_keywords(payload: dict) -> list[str]:
    dna = coerce_dict(payload.get("project_dna"))
    raw = dna.get("brand_keywords") or payload.get("brand_keywords") or []
    if isinstance(raw, str):
        return [w.strip() for w in re.split(r"[,;]", raw) if w.strip()]
    if isinstance(raw, list):
        return [str(w).strip() for w in raw if str(w).strip()]
    return []


def _trend_keywords(payload: dict) -> list[str]:
    trend = coerce_dict(payload.get("trend_intelligence") or payload.get("trend_report"))
    keywords = trend.get("keywords") or trend.get("hashtags") or []
    if isinstance(keywords, list):
        return [str(k) for k in keywords[:5]]
    return []


def _title_variants(topic: str, hook: str) -> list[str]:
    base = _truncate(hook or topic, 70)
    variants = [base]
    if topic and topic.lower() not in base.lower():
        variants.append(_truncate(f"{topic} — você precisa ver isso", 70))
    if hook:
        variants.append(_truncate(f"Por que {topic} está bombando?", 70))
    if "?" not in base:
        variants.append(_truncate(f"{base}?", 70))
    out: list[str] = []
    for v in variants:
        if v and v not in out:
            out.append(v)
    return out[:3]


def _build_description(topic: str, hook: str, body: str, cta: str, keywords: list[str]) -> str:
    lead = hook or topic
    snippet = _truncate(body, 280) if body else ""
    kw_line = " ".join(f"#{k}" for k in keywords[:4]) if keywords else ""
    parts = [lead]
    if snippet and snippet != lead:
        parts.append(snippet)
    if cta:
        parts.append(cta)
    if kw_line:
        parts.append(kw_line)
    return _truncate("\n\n".join(p for p in parts if p), 500)


def _score_package(title: str, description: str, hashtags: list[str], keywords: list[str]) -> float:
    score = 40.0
    if 15 <= len(title) <= 70:
        score += 20.0
    if 80 <= len(description) <= 500:
        score += 20.0
    elif 40 <= len(description) < 80:
        score += 10.0
    if 5 <= len(hashtags) <= 12:
        score += 15.0
    if keywords:
        score += 10.0
    if any(w in title.lower() for w in ("como", "por que", "guia", "dicas", "segredo")):
        score += 5.0
    return _clamp_score(score)


def _recommendations(title: str, description: str, hashtags: list[str]) -> list[str]:
    tips: list[str] = []
    if len(title) > 70:
        tips.append("Encurte o título para melhor CTR em mobile.")
    if len(description) < 80:
        tips.append("Expanda a descrição com palavras-chave do tema.")
    if len(hashtags) < 5:
        tips.append("Adicione mais hashtags de nicho (5–10).")
    if not tips:
        tips.append("Metadados prontos para publicação.")
    return tips


def _platform_copy(platform: str, title: str, description: str, hashtags: list[str]) -> PlatformSeo:
    platform_tags = _unique_tags(hashtags, _PLATFORM_HASHTAGS.get(platform, []), limit=10)
    if platform == "youtube_shorts":
        desc = _truncate(f"{description}\n\n#Shorts", 500)
        ttl = _truncate(title, 100)
    elif platform == "tiktok":
        desc = _truncate(description, 220)
        ttl = _truncate(title, 80)
    else:
        desc = _truncate(description, 300)
        ttl = _truncate(title, 80)
    return PlatformSeo(platform=platform, title=ttl, description=desc, hashtags=platform_tags)


class SeoOptimizer:
    """Heuristic SEO for short-form video publication metadata."""

    def optimize(self, payload: dict[str, Any]) -> SeoPackage:
        ctx = _script_context(payload)
        topic = ctx["topic"] or "Conteúdo"
        brand = _brand_keywords(payload)
        trend = _trend_keywords(payload)
        topic_words = [w for w in _words(topic) if w not in _STOPWORDS][:4]
        keywords = _unique_tags(brand, trend, topic_words, limit=8)
        title_variants = _title_variants(topic, ctx["hook"])
        title = title_variants[0] if title_variants else _truncate(topic, 70)
        hashtags = _unique_tags(brand, trend, topic_words, _PLATFORM_HASHTAGS["tiktok"], limit=10)
        description = _build_description(topic, ctx["hook"], ctx["body"], ctx["cta"], keywords)
        platforms = [_platform_copy(p, title, description, hashtags) for p in _PLATFORMS]
        score = _score_package(title, description, hashtags, keywords)
        return SeoPackage(
            title=title,
            description=description,
            hashtags=hashtags,
            keywords=keywords,
            title_variants=title_variants,
            platforms=platforms,
            seo_score=score,
            recommendations=_recommendations(title, description, hashtags),
        )
