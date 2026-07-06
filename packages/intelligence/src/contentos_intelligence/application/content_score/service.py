"""ContentScoreService — unified 0–100 facade (Epic 9)."""

from __future__ import annotations

import json
import os

from contentos_intelligence.application.content_score.dimensions import (
    DEFAULT_WEIGHTS,
    EXTRACTORS,
    _clamp_100,
)
from contentos_intelligence.domain.content_score import ContentScoreDimension, ContentScoreReport
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.interfaces import IKnowledgeQuery
from contentos_intelligence.domain.knowledge import KnowledgeQueryRequest


def _content_score_enabled() -> bool:
    return os.getenv("CONTENT_SCORE_ENABLED", "true").lower() in ("1", "true", "yes")


def _load_weights() -> dict[str, float]:
    raw = os.getenv("CONTENT_SCORE_WEIGHTS", "").strip()
    if not raw:
        return dict(DEFAULT_WEIGHTS)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            weights = {str(k): float(v) for k, v in parsed.items()}
            total = sum(weights.values())
            if total > 0:
                return {k: v / total for k, v in weights.items()}
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return dict(DEFAULT_WEIGHTS)


def _grade(score: float) -> str:
    if score >= 90:
        return "excelente"
    if score >= 75:
        return "bom"
    if score >= 60:
        return "medio"
    return "precisa_melhorar"


def _summary(score: float, grade: str) -> str:
    labels = {
        "excelente": "Conteúdo com alta probabilidade de performance.",
        "bom": "Boa base — ajustes pontuais podem elevar o resultado.",
        "medio": "Score mediano — revisar gancho, retenção ou CTA.",
        "precisa_melhorar": "Score baixo — priorize melhorias antes de publicar.",
    }
    return f"{labels.get(grade, '')} Nota {score:.0f}/100 ({grade})."


class ContentScoreService:
    """Aggregates V3/V4 signals into a single 0–100 report."""

    def __init__(self, knowledge_query: IKnowledgeQuery | None = None) -> None:
        self._kb = knowledge_query
        self._weights = _load_weights()

    async def score(self, context: IntelligenceContext) -> ContentScoreReport:
        payload = dict(context.payload or {})
        dimensions: list[ContentScoreDimension] = []

        for name, extractor in EXTRACTORS.items():
            weight = self._weights.get(name, 0.0)
            if weight <= 0:
                continue
            value, source = extractor(payload)
            dimensions.append(
                ContentScoreDimension(name=name, score=value, weight=weight, source=source)
            )

        originality_weight = self._weights.get("originality", 0.0)
        if originality_weight > 0:
            orig_score, orig_source = await self._originality(context, payload)
            dimensions.append(
                ContentScoreDimension(
                    name="originality",
                    score=orig_score,
                    weight=originality_weight,
                    source=orig_source,
                )
            )

        total = 0.0
        for dim in dimensions:
            total += dim.score * dim.weight
        total = _clamp_100(total)
        grade = _grade(total)

        return ContentScoreReport(
            total_score=total,
            dimensions=dimensions,
            summary=_summary(total, grade),
            grade=grade,
            mode=self._mode(payload),
        )

    def _mode(self, payload: dict) -> str:
        if payload.get("quality_score") is not None or payload.get("video_score") is not None:
            return "full"
        return "preview"

    async def _originality(self, context: IntelligenceContext, payload: dict) -> tuple[float, str]:
        if not self._kb:
            return 50.0, "neutral"
        script = payload.get("script") or {}
        query = str(context.topic or "")
        if isinstance(script, dict):
            query = query or str(script.get("title") or script.get("hook") or "")[:200]
        if not query.strip():
            return 50.0, "neutral"
        try:
            hits = await self._kb.search(
                KnowledgeQueryRequest(
                    project_id=context.project_id,
                    query=query[:500],
                    limit=3,
                )
            )
        except Exception:
            return 50.0, "kb_unavailable"
        if not hits:
            return 85.0, "kb_no_similar"
        max_sim = max(float(h.similarity) for h in hits)
        return _clamp_100(100.0 - max_sim * 100.0), "kb_inverse_similarity"


def is_content_score_enabled() -> bool:
    return _content_score_enabled()
