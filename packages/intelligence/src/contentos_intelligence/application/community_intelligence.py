"""Community Intelligence — turns comments into strategic signals.

This module does not post replies. It converts comment analyses and reply drafts
into FAQ, pains, objections, requests, content ideas, campaigns and audience
signals that can influence objectives and calendar planning.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

QUESTION_HINTS = ("?", "quando", "como", "qual", "onde", "por que", "pq", "what", "how", "when", "why")
OBJECTION_HINTS = ("fake", "clickbait", "não acredito", "nao acredito", "mentira", "caro", "ruim", "chato")
REQUEST_HINTS = ("faz", "faça", "faz sobre", "parte 2", "mais", "traz", "explica", "tutorial", "react")
PAIN_HINTS = ("não entendi", "nao entendi", "confuso", "difícil", "dificil", "travou", "erro", "problema")


@dataclass(frozen=True)
class CommunitySignal:
    kind: str
    title: str
    detail: str
    priority: str = "medium"
    evidence_count: int = 1
    source: str = "community_intelligence"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "detail": self.detail,
            "priority": self.priority,
            "evidence_count": self.evidence_count,
            "source": self.source,
        }


@dataclass(frozen=True)
class CommunityIntelligenceReport:
    project_id: str
    status: str
    summary: str
    total_comments: int = 0
    faq: list[CommunitySignal] = field(default_factory=list)
    pains: list[CommunitySignal] = field(default_factory=list)
    objections: list[CommunitySignal] = field(default_factory=list)
    requests: list[CommunitySignal] = field(default_factory=list)
    video_ideas: list[CommunitySignal] = field(default_factory=list)
    campaign_ideas: list[CommunitySignal] = field(default_factory=list)
    audience_updates: list[CommunitySignal] = field(default_factory=list)
    calendar_influence: list[dict[str, Any]] = field(default_factory=list)
    objective_influence: list[dict[str, Any]] = field(default_factory=list)
    reply_guardrails: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "summary": self.summary,
            "total_comments": self.total_comments,
            "faq": [item.to_dict() for item in self.faq],
            "pains": [item.to_dict() for item in self.pains],
            "objections": [item.to_dict() for item in self.objections],
            "requests": [item.to_dict() for item in self.requests],
            "video_ideas": [item.to_dict() for item in self.video_ideas],
            "campaign_ideas": [item.to_dict() for item in self.campaign_ideas],
            "audience_updates": [item.to_dict() for item in self.audience_updates],
            "calendar_influence": [dict(item) for item in self.calendar_influence],
            "objective_influence": [dict(item) for item in self.objective_influence],
            "reply_guardrails": list(self.reply_guardrails),
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list | tuple) else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _priority(count: int, *, high: int = 4) -> str:
    if count >= high:
        return "high"
    if count >= 2:
        return "medium"
    return "low"


def _contains(text: str, hints: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in hints)


def _top_themes(comment_insights: list[dict[str, Any]], *, limit: int = 8) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for row in comment_insights:
        for theme in _as_list(row.get("themes")):
            cleaned = _text(theme).lower()
            if cleaned:
                counter[cleaned] += max(1, int(row.get("comment_count") or 1))
    return counter.most_common(limit)


def _sample_comments(comment_insights: list[dict[str, Any]], drafts: list[dict[str, Any]]) -> list[str]:
    samples: list[str] = []
    for row in comment_insights:
        samples.extend(_text(item) for item in _as_list(row.get("sample_comments")))
    for draft in drafts:
        samples.append(_text(draft.get("original_comment")))
    seen: set[str] = set()
    out: list[str] = []
    for item in samples:
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
    return out[:80]


def build_community_intelligence_report(
    *,
    project_id: str,
    comment_insights: list[Mapping[str, Any] | Any] | None = None,
    community_drafts: list[Mapping[str, Any] | Any] | None = None,
) -> CommunityIntelligenceReport:
    insights = [_as_dict(item) for item in comment_insights or []]
    drafts = [_as_dict(item) for item in community_drafts or []]
    comments = _sample_comments(insights, drafts)
    total_comments = sum(int(row.get("comment_count") or 0) for row in insights)
    themes = _top_themes(insights)

    faq: list[CommunitySignal] = []
    pains: list[CommunitySignal] = []
    objections: list[CommunitySignal] = []
    requests: list[CommunitySignal] = []

    for comment in comments:
        if _contains(comment, QUESTION_HINTS):
            faq.append(CommunitySignal("faq", "Responder dúvida recorrente", comment[:240], priority="medium"))
        if _contains(comment, PAIN_HINTS):
            pains.append(CommunitySignal("pain", "Dor ou dificuldade do público", comment[:240], priority="high"))
        if _contains(comment, OBJECTION_HINTS):
            objections.append(CommunitySignal("objection", "Objeção ou desconfiança detectada", comment[:240], priority="high"))
        if _contains(comment, REQUEST_HINTS):
            requests.append(CommunitySignal("request", "Pedido explícito da comunidade", comment[:240], priority="medium"))

    for draft in drafts:
        category = _text(draft.get("category"))
        original = _text(draft.get("original_comment"))
        priority = "high" if int(draft.get("priority") or 0) >= 80 else "medium"
        if category == "question" and original:
            faq.append(CommunitySignal("faq", "Dúvida priorizada pelo Community Agent", original[:240], priority=priority))
        elif category == "support" and original:
            pains.append(CommunitySignal("pain", "Comentário que precisa suporte", original[:240], priority=priority))

    faq = _dedupe(faq, limit=10)
    pains = _dedupe(pains, limit=10)
    objections = _dedupe(objections, limit=10)
    requests = _dedupe(requests, limit=10)

    video_ideas = [
        CommunitySignal(
            "video_idea",
            f"Vídeo respondendo comunidade: {theme}",
            f"Criar conteúdo curto explicando {theme}, usando perguntas e comentários como gancho.",
            priority=_priority(count),
            evidence_count=count,
        )
        for theme, count in themes[:6]
    ]
    for req in requests[:3]:
        video_ideas.append(
            CommunitySignal(
                "video_idea",
                "Vídeo pedido pela comunidade",
                req.detail,
                priority=req.priority,
                evidence_count=req.evidence_count,
            )
        )
    video_ideas = _dedupe(video_ideas, limit=10)

    campaign_ideas = [
        CommunitySignal(
            "campaign_idea",
            f"Série de comunidade sobre {theme}",
            f"Agrupar dúvidas, objeções e pedidos sobre {theme} em uma sequência de posts/vídeos.",
            priority=_priority(count, high=6),
            evidence_count=count,
        )
        for theme, count in themes[:4]
    ]
    audience_updates = [
        CommunitySignal(
            "audience_update",
            "Atualizar Audience Intelligence com temas recorrentes",
            ", ".join(theme for theme, _ in themes[:6]) or "Sem temas suficientes.",
            priority="high" if themes else "low",
            evidence_count=sum(count for _, count in themes[:6]),
        )
    ]

    calendar_influence = [
        {
            "type": "calendar_seed",
            "topic": item.title,
            "detail": item.detail,
            "priority": item.priority,
            "source": item.source,
        }
        for item in video_ideas[:6]
    ]
    objective_influence = [
        {
            "type": "objective_signal",
            "area": "audience",
            "title": item.title,
            "detail": item.detail,
            "priority": item.priority,
            "source": item.source,
        }
        for item in [*pains[:3], *objections[:3], *audience_updates[:1]]
    ]

    signal_count = len(faq) + len(pains) + len(objections) + len(requests) + len(video_ideas)
    status = "ready" if signal_count else "learning"
    summary = f"Community Intelligence {status}: {total_comments} comentário(s), {signal_count} sinal(is) estratégicos."
    return CommunityIntelligenceReport(
        project_id=project_id,
        status=status,
        summary=summary,
        total_comments=total_comments,
        faq=faq,
        pains=pains,
        objections=objections,
        requests=requests,
        video_ideas=video_ideas,
        campaign_ideas=_dedupe(campaign_ideas, limit=6),
        audience_updates=audience_updates,
        calendar_influence=calendar_influence,
        objective_influence=objective_influence,
        reply_guardrails=[
            "Não responder automaticamente sem configuração explícita.",
            "Rascunhos de resposta permanecem em aprovação humana.",
            "Insights podem alimentar objetivos e calendário, mas não publicam conteúdo sozinhos.",
        ],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _dedupe(items: list[CommunitySignal], *, limit: int) -> list[CommunitySignal]:
    seen: set[tuple[str, str]] = set()
    out: list[CommunitySignal] = []
    for item in items:
        key = (item.kind, item.detail.lower())
        if not item.detail or key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out
