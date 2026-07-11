"""Learning loop for Social Autopilot.

Converts social observability into actionable improvements for the next cycle.
It does not mutate memory, calendar or publishing state; it returns explicit
recommendations that can be reviewed or persisted by existing services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

SocialLearningStatus = Literal["learning", "ready", "blocked", "empty"]


@dataclass(frozen=True)
class SocialLearningRecommendation:
    area: str
    title: str
    detail: str
    priority: str = "medium"
    action: str = "review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "title": self.title,
            "detail": self.detail,
            "priority": self.priority,
            "action": self.action,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SocialLearningReport:
    project_id: str
    status: SocialLearningStatus
    score: int
    summary: str
    learned: list[str] = field(default_factory=list)
    recommendations: list[SocialLearningRecommendation] = field(default_factory=list)
    memory_candidates: list[SocialLearningRecommendation] = field(default_factory=list)
    next_cycle: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "score": self.score,
            "summary": self.summary,
            "learned": list(self.learned),
            "recommendations": [item.to_dict() for item in self.recommendations],
            "memory_candidates": [item.to_dict() for item in self.memory_candidates],
            "next_cycle": dict(self.next_cycle),
            "blockers": list(self.blockers),
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _unique(values: list[Any], *, limit: int = 12) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.lower()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
        if len(out) >= limit:
            break
    return out


def _priority_from_score(score: int) -> str:
    if score < 60:
        return "high"
    if score < 85:
        return "medium"
    return "low"


def build_social_learning_report(
    *,
    project_id: str,
    observability: Mapping[str, Any] | Any | None = None,
    performance_rows: list[Mapping[str, Any] | Any] | None = None,
    community_signals: Mapping[str, Any] | Any | None = None,
) -> SocialLearningReport:
    obs = _as_dict(observability or {})
    counts = _as_dict(obs.get("counts"))
    lifecycle = _as_dict(obs.get("lifecycle"))
    performance = [_as_dict(item) for item in performance_rows or []]
    community = _as_dict(community_signals or {})
    score = int(obs.get("readiness_score") or 0)
    obs_status = str(obs.get("status") or "empty")

    learned: list[str] = []
    recommendations: list[SocialLearningRecommendation] = []
    memory_candidates: list[SocialLearningRecommendation] = []
    blockers: list[str] = []

    operations = int(counts.get("operations") or 0)
    ready_items = int(counts.get("ready_items") or 0)
    review_items = int(counts.get("review_items") or 0)
    blocked_items = int(counts.get("blocked_items") or 0)
    dispatch_commands = int(counts.get("dispatch_commands") or 0)

    if operations == 0:
        recommendations.append(
            SocialLearningRecommendation(
                area="planning",
                title="Gerar primeiro plano social",
                detail="Sem operações sociais observadas; crie calendário, sinais de comunidade ou performance para iniciar o ciclo.",
                priority="high",
                action="build_social_plan",
            )
        )
    else:
        learned.append(
            f"Ciclo social analisou {operations} operação(ões): {ready_items} pronta(s), {review_items} revisão(ões), {blocked_items} bloqueada(s)."
        )

    for risk in _unique(_as_list(obs.get("risks")), limit=8):
        blockers.append(risk)
        recommendations.append(
            SocialLearningRecommendation(
                area="governance",
                title=f"Resolver risco social: {risk}",
                detail="Risco detectado pela governança/observabilidade antes de publicar ou despachar.",
                priority="high",
                action="resolve_social_risk",
                metadata={"risk": risk},
            )
        )

    for action in _unique(_as_list(obs.get("manual_actions")), limit=8):
        recommendations.append(
            SocialLearningRecommendation(
                area="operations",
                title="Concluir ação manual pendente",
                detail=action,
                priority="high" if blocked_items else "medium",
                action="manual_review",
            )
        )

    if review_items:
        recommendations.append(
            SocialLearningRecommendation(
                area="approval",
                title="Reduzir atrito da fila de aprovação",
                detail=f"Há {review_items} item(ns) aguardando revisão. Padronize critérios para acelerar o próximo ciclo.",
                priority="medium",
                action="refine_approval_policy",
                metadata={"review_items": review_items},
            )
        )

    if dispatch_commands:
        learned.append(f"Dispatch preparou {dispatch_commands} comando(s) para serviços existentes.")
    elif operations and not blocked_items:
        recommendations.append(
            SocialLearningRecommendation(
                area="dispatch",
                title="Preparar dispatch do próximo lote",
                detail="Existem operações sociais, mas nenhum comando de dispatch foi preparado.",
                priority="medium",
                action="build_dispatch_plan",
            )
        )

    high_performers = [row for row in performance if str(row.get("performance_tier") or "").lower() == "high"]
    for row in high_performers[:3]:
        title = str(row.get("title") or row.get("topic") or "Conteúdo vencedor")
        learned.append(f"Conteúdo vencedor detectado: {title[:120]}")
        memory_candidates.append(
            SocialLearningRecommendation(
                area="memory",
                title="Salvar padrão social vencedor",
                detail=title,
                priority="high",
                action="update_channel_memory",
                metadata={"platform": row.get("platform"), "source": "performance"},
            )
        )

    for idea in _as_list(community.get("video_ideas"))[:3]:
        raw = _as_dict(idea)
        title = str(raw.get("title") or "Sinal da comunidade")
        recommendations.append(
            SocialLearningRecommendation(
                area="community",
                title="Transformar sinal da comunidade em novo teste",
                detail=title,
                priority=str(raw.get("priority") or "medium"),
                action="add_to_social_calendar",
                metadata={"source": "community"},
            )
        )

    if score < 70 and operations:
        recommendations.append(
            SocialLearningRecommendation(
                area="quality",
                title="Melhorar prontidão social antes do próximo ciclo",
                detail=f"Score social atual {score}/100. Resolva bloqueios/revisões antes de aumentar automação.",
                priority=_priority_from_score(score),
                action="improve_social_readiness",
            )
        )

    if obs_status == "blocked":
        status: SocialLearningStatus = "blocked"
    elif obs_status == "empty":
        status = "empty"
    elif score >= 85 and not blockers:
        status = "ready"
    else:
        status = "learning"

    next_cycle = {
        "refresh_plan": operations == 0 or bool(recommendations),
        "review_queue": review_items > 0,
        "resolve_blockers": len(blockers),
        "dispatch_ready": dispatch_commands > 0 and not blockers,
        "update_memory": bool(memory_candidates),
        "plan_status": lifecycle.get("plan_status", "unknown"),
        "queue_status": lifecycle.get("queue_status", "unknown"),
        "dispatch_status": lifecycle.get("dispatch_status", "unknown"),
    }
    summary = (
        f"Social learning {status}: score {score}/100, "
        f"{len(learned)} aprendizado(s), {len(recommendations)} recomendação(ões)."
    )
    return SocialLearningReport(
        project_id=project_id,
        status=status,
        score=score,
        summary=summary,
        learned=_unique(learned, limit=10),
        recommendations=recommendations[:12],
        memory_candidates=memory_candidates[:8],
        next_cycle=next_cycle,
        blockers=_unique(blockers, limit=8),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
