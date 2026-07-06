"""Heuristic text generators from script — Epic 2a (no LLM)."""

from __future__ import annotations

import re
from typing import Any

from contentos_intelligence.domain.multi_content import TextArtifact


def _script_text(payload: dict) -> tuple[str, str]:
    script = payload.get("script") or {}
    if not isinstance(script, dict):
        script = {}
    title = str(script.get("title") or payload.get("topic") or "Conteúdo")
    full = str(
        script.get("full_text")
        or " ".join(str(script.get(k) or "") for k in ("hook", "development", "curiosity", "call_to_action"))
        or title
    ).strip()
    return title, full


def _sentences(text: str, limit: int = 8) -> list[str]:
    parts = re.split(r"[.!?]\s+", text)
    out = [p.strip() for p in parts if p.strip()]
    return out[:limit]


def generate_thread_x(payload: dict) -> TextArtifact:
    title, full = _script_text(payload)
    sents = _sentences(full, 5)
    if not sents:
        sents = [title]
    posts = [{"order": i + 1, "text": (s[:270] + "…") if len(s) > 270 else s} for i, s in enumerate(sents)]
    content = "\n\n---\n\n".join(f"{p['order']}/ {p['text']}" for p in posts)
    return TextArtifact(
        format="thread_x",
        title=f"Thread: {title}",
        content=content,
        data={"posts": posts, "hook_tweet": posts[0] if posts else {"text": title}},
        source="heuristic",
    )


def generate_linkedin_post(payload: dict) -> TextArtifact:
    title, full = _script_text(payload)
    hook = _sentences(full, 1)[0] if full else title
    body = f"{hook}\n\n{full[:1200]}".strip()
    if len(full) > 200:
        body += "\n\n💡 Qual sua opinião? Comenta abaixo."
    return TextArtifact(
        format="linkedin_post",
        title=title,
        content=body[:3000],
        data={"hashtags": ["conteúdo", "criadores", "aprendizado"]},
        source="heuristic",
    )


def generate_newsletter(payload: dict) -> TextArtifact:
    title, full = _script_text(payload)
    script = payload.get("script") or {}
    cta = ""
    if isinstance(script, dict):
        cta = str(script.get("call_to_action") or "")
    content = (
        f"# {title}\n\n"
        f"Olá! Nesta edição:\n\n"
        f"{full}\n\n"
        f"---\n\n"
        f"{cta or 'Até a próxima!'}"
    )
    return TextArtifact(
        format="newsletter",
        title=title,
        content=content,
        data={"subject": f"📬 {title}", "preview_text": full[:120]},
        source="heuristic",
    )


def generate_seo_article(payload: dict) -> TextArtifact:
    title, full = _script_text(payload)
    topic = str(payload.get("topic") or title)
    meta = f"Guia completo sobre {topic}. Aprenda insights práticos em poucos minutos."
    content = (
        f"# {title}\n\n"
        f"## Introdução\n{full[:400]}\n\n"
        f"## Desenvolvimento\n{full}\n\n"
        f"## Conclusão\n"
        f"Compartilhe este artigo se foi útil."
    )
    return TextArtifact(
        format="seo_article",
        title=title,
        content=content,
        data={
            "meta_description": meta[:160],
            "slug": re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:80],
            "keywords": [w for w in topic.lower().split() if len(w) > 3][:8],
        },
        source="heuristic",
    )


def generate_email_marketing(payload: dict) -> TextArtifact:
    title, full = _script_text(payload)
    script = payload.get("script") or {}
    cta = "Saiba mais"
    if isinstance(script, dict) and script.get("call_to_action"):
        cta = str(script["call_to_action"])[:80]
    content = (
        f"Assunto: {title}\n\n"
        f"Oi!\n\n"
        f"{full[:1500]}\n\n"
        f"[{cta}]\n\n"
        f"Abraços,\nEquipe ContentOS"
    )
    return TextArtifact(
        format="email_marketing",
        title=title,
        content=content,
        data={"subject": title, "preheader": full[:90]},
        source="heuristic",
    )


GENERATORS = {
    "thread_x": generate_thread_x,
    "linkedin_post": generate_linkedin_post,
    "newsletter": generate_newsletter,
    "seo_article": generate_seo_article,
    "email_marketing": generate_email_marketing,
}


def merge_llm_artifact(fmt: str, llm_data: dict[str, Any], fallback: TextArtifact) -> TextArtifact:
    """Merge LLM JSON into artifact, keeping fallback on missing fields."""
    title = str(llm_data.get("title") or fallback.title)
    content = str(llm_data.get("content") or llm_data.get("body") or llm_data.get("full_text") or fallback.content)
    extra = {k: v for k, v in llm_data.items() if k not in ("title", "content", "body", "full_text")}
    return TextArtifact(
        format=fmt,
        title=title,
        content=content,
        data={**fallback.data, **extra},
        source="llm",
    )
