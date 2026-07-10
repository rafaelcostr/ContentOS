"""Closed-loop learning report for Growth Autopilot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from contentos_growth.application.autonomous_execution import AutonomousExecutionPlan
from contentos_growth.application.performance_learning_interpreter import PerformanceInterpretation
from contentos_growth.domain import GrowthReport

LoopStatus = Literal["learning", "ready", "blocked"]


@dataclass(frozen=True)
class ClosedLoopRecommendation:
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
class ClosedLoopReport:
    project_id: str
    status: LoopStatus
    summary: str
    score: int
    learned: list[str] = field(default_factory=list)
    strategy_updates: list[ClosedLoopRecommendation] = field(default_factory=list)
    calendar_updates: list[ClosedLoopRecommendation] = field(default_factory=list)
    execution_updates: list[ClosedLoopRecommendation] = field(default_factory=list)
    memory_updates: list[ClosedLoopRecommendation] = field(default_factory=list)
    next_cycle: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "summary": self.summary,
            "score": self.score,
            "learned": list(self.learned),
            "strategy_updates": [item.to_dict() for item in self.strategy_updates],
            "calendar_updates": [item.to_dict() for item in self.calendar_updates],
            "execution_updates": [item.to_dict() for item in self.execution_updates],
            "memory_updates": [item.to_dict() for item in self.memory_updates],
            "next_cycle": dict(self.next_cycle),
            "blockers": list(self.blockers),
            "generated_at": self.generated_at,
        }


def _priority(score: float | int | None) -> str:
    value = float(score or 0)
    if value < 45:
        return "high"
    if value < 70:
        return "medium"
    return "low"


def _unique(items: list[Any], *, limit: int = 12) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        key = text.lower()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
        if len(out) >= limit:
            break
    return out


def build_closed_loop_report(
    *,
    project_id: str,
    growth_report: GrowthReport,
    performance: PerformanceInterpretation,
    execution_plan: AutonomousExecutionPlan | None = None,
    saved_recommendations: int = 0,
) -> ClosedLoopReport:
    learned: list[str] = []
    strategy_updates: list[ClosedLoopRecommendation] = []
    calendar_updates: list[ClosedLoopRecommendation] = []
    execution_updates: list[ClosedLoopRecommendation] = []
    memory_updates: list[ClosedLoopRecommendation] = []
    blockers: list[str] = []

    if performance.total_media == 0:
        blockers.append("Sem dados de performance pos-publicacao para fechar o ciclo.")
        execution_updates.append(
            ClosedLoopRecommendation(
                area="performance",
                title="Sincronizar analytics das plataformas",
                detail="Conecte OAuth/API e execute Performance Learning apos publicacoes reais.",
                priority="high",
                action="sync_performance",
            )
        )
    else:
        learned.append(
            f"{performance.total_media} midia(s) analisada(s): "
            f"{performance.high_performers} alta performance, {performance.low_performers} baixa performance."
        )

    if performance.top_hooks:
        learned.append(f"Hook vencedor: {performance.top_hooks[0][:120]}")
        memory_updates.append(
            ClosedLoopRecommendation(
                area="memory",
                title="Salvar hooks vencedores na memoria do canal",
                detail=performance.top_hooks[0],
                priority="high",
                action="update_channel_memory",
                metadata={"top_hooks": performance.top_hooks[:5]},
            )
        )

    for opportunity in performance.opportunities[:3]:
        strategy_updates.append(
            ClosedLoopRecommendation(
                area="strategy",
                title="Escalar oportunidade detectada",
                detail=opportunity,
                priority="high",
                action="update_strategy",
            )
        )
        calendar_updates.append(
            ClosedLoopRecommendation(
                area="calendar",
                title="Planejar nova variacao vencedora",
                detail=opportunity,
                priority="high",
                action="autonomous_calendar",
            )
        )

    for risk in performance.risks[:3]:
        strategy_updates.append(
            ClosedLoopRecommendation(
                area="quality",
                title="Corrigir risco de performance",
                detail=risk,
                priority="medium",
                action="review_strategy",
            )
        )

    if growth_report.risks:
        blockers.extend(growth_report.risks[:3])

    if execution_plan:
        ready_actions = len(execution_plan.actions)
        blocked_actions = len(execution_plan.blocked_actions)
        learned.append(f"Autopiloto: {ready_actions} acao(oes) pronta(s), {blocked_actions} bloqueada(s).")
        if ready_actions:
            execution_updates.append(
                ClosedLoopRecommendation(
                    area="execution",
                    title="Executar proximo lote assistido",
                    detail=f"{ready_actions} acao(oes) prontas no plano de execucao.",
                    priority="high",
                    action="autopilot_run",
                )
            )
        for action in execution_plan.blocked_actions[:3]:
            execution_updates.append(
                ClosedLoopRecommendation(
                    area="execution",
                    title=f"Desbloquear {action.action}",
                    detail=action.block_reason or action.detail,
                    priority=action.priority,
                    action="resolve_blocker",
                    metadata={"calendar_item_id": action.calendar_item_id, "channel_id": action.channel_id},
                )
            )

    if saved_recommendations:
        learned.append(f"{saved_recommendations} recomendacao(oes) nova(s) salva(s) para o proximo ciclo.")

    score = int(
        min(
            100,
            round(
                float(growth_report.score or 0) * 0.5
                + min(performance.total_media * 3, 25)
                + min(performance.high_performers * 10, 20)
                + min(len(learned) * 5, 15)
                + (10 if execution_plan and execution_plan.actions else 0)
            ),
        )
    )

    if blockers and performance.total_media == 0:
        status: LoopStatus = "blocked"
    elif score >= 60:
        status = "ready"
    else:
        status = "learning"

    next_cycle = {
        "sync_performance": performance.total_media == 0,
        "update_memory": bool(memory_updates),
        "refresh_calendar": bool(calendar_updates),
        "run_autopilot": bool(execution_plan and execution_plan.actions),
        "review_blockers": len(blockers),
    }
    summary = (
        f"Loop fechado {status}: score {score}/100, "
        f"{len(learned)} aprendizado(s), {len(blockers)} bloqueio(s)."
    )

    return ClosedLoopReport(
        project_id=project_id,
        status=status,
        summary=summary,
        score=score,
        learned=_unique(learned, limit=10),
        strategy_updates=strategy_updates[:8],
        calendar_updates=calendar_updates[:8],
        execution_updates=execution_updates[:8],
        memory_updates=memory_updates[:8],
        next_cycle=next_cycle,
        blockers=_unique(blockers, limit=8),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
