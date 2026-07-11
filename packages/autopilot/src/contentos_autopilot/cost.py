"""Cost intelligence contracts for Autopilot.

This module estimates cost and recommends execution mode. It does not consume
credits, enforce billing, start pipelines or mutate quotas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

ExecutionCostMode = Literal["economy", "standard", "aggressive"]
CostStatus = Literal["ready", "approval_required", "blocked"]


@dataclass(frozen=True)
class CostDecisionScore:
    status: CostStatus
    mode: ExecutionCostMode
    quantity: int
    credit_cost_per_pipeline: int
    total_credit_cost: int
    credits_balance: int | None = None
    credits_ok: bool = True
    monthly_quota: int = 0
    monthly_used: int = 0
    monthly_remaining: int | None = None
    concurrent_limit: int = 0
    concurrent_active: int = 0
    quota_ok: bool = True
    cost_score: int = 100
    estimated_ai_cost_units: int = 0
    recommendations: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "mode": self.mode,
            "quantity": self.quantity,
            "credit_cost_per_pipeline": self.credit_cost_per_pipeline,
            "total_credit_cost": self.total_credit_cost,
            "credits_balance": self.credits_balance,
            "credits_ok": self.credits_ok,
            "monthly_quota": self.monthly_quota,
            "monthly_used": self.monthly_used,
            "monthly_remaining": self.monthly_remaining,
            "concurrent_limit": self.concurrent_limit,
            "concurrent_active": self.concurrent_active,
            "quota_ok": self.quota_ok,
            "cost_score": self.cost_score,
            "estimated_ai_cost_units": self.estimated_ai_cost_units,
            "recommendations": list(self.recommendations),
            "blockers": list(self.blockers),
            "guardrails": list(self.guardrails),
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _is_unlimited(limit: int) -> bool:
    return int(limit or 0) <= 0


def _media_cost_units(media_strategy: Mapping[str, Any] | Any | None) -> int:
    media = _as_dict(media_strategy or {})
    units = 0
    for item in media.get("source_mix") or []:
        if not isinstance(item, Mapping):
            continue
        percentage = int(item.get("percentage") or 0)
        source = str(item.get("source") or "")
        if source == "ai_video":
            units += max(1, percentage // 10) * 8
        elif source == "ai_image":
            units += max(1, percentage // 10) * 3
        elif source in {"pexels", "pixabay"}:
            units += max(1, percentage // 25)
        elif source in {"own_library", "motion_graphics", "infographic"}:
            units += max(0, percentage // 40)
    return units


def build_cost_decision_score(
    *,
    quantity: int = 1,
    credit_cost_per_pipeline: int = 1,
    credits_balance: int | None = None,
    monthly_quota: int = 0,
    monthly_used: int = 0,
    concurrent_limit: int = 0,
    concurrent_active: int = 0,
    media_strategy: Mapping[str, Any] | Any | None = None,
    require_manual_approval_above: int = 10,
) -> CostDecisionScore:
    qty = max(1, int(quantity or 1))
    per = max(1, int(credit_cost_per_pipeline or 1))
    total = qty * per
    ai_units = _media_cost_units(media_strategy)
    total_with_ai = total + ai_units

    monthly_remaining = None
    monthly_ok = True
    if not _is_unlimited(monthly_quota):
        monthly_remaining = max(0, int(monthly_quota) - int(monthly_used))
        monthly_ok = qty <= monthly_remaining

    concurrent_ok = True
    if not _is_unlimited(concurrent_limit):
        concurrent_ok = int(concurrent_active) + qty <= int(concurrent_limit)

    credits_ok = True
    if credits_balance is not None:
        credits_ok = int(credits_balance) >= total

    blockers: list[str] = []
    if not credits_ok:
        blockers.append(f"Créditos insuficientes: {credits_balance} disponível(is), {total} necessário(s).")
    if not monthly_ok:
        blockers.append(f"Quota mensal insuficiente: restam {monthly_remaining}, pedido {qty}.")
    if not concurrent_ok:
        blockers.append("Limite de pipelines simultâneos seria excedido.")

    recommendations: list[str] = []
    mode: ExecutionCostMode = "standard"
    if total_with_ai >= require_manual_approval_above:
        mode = "economy"
        recommendations.append("Usar modo econômico e preferir biblioteca própria/modelos locais.")
    elif ai_units >= 4:
        recommendations.append("Revisar uso de mídia IA/externa antes de produzir.")
    else:
        recommendations.append("Custo estimado dentro do padrão.")

    if blockers:
        status: CostStatus = "blocked"
    elif total_with_ai >= require_manual_approval_above:
        status = "approval_required"
    else:
        status = "ready"

    penalty = min(80, total_with_ai * 4)
    if blockers:
        penalty += 20
    cost_score = max(0, min(100, 100 - penalty))

    return CostDecisionScore(
        status=status,
        mode=mode,
        quantity=qty,
        credit_cost_per_pipeline=per,
        total_credit_cost=total,
        credits_balance=credits_balance,
        credits_ok=credits_ok,
        monthly_quota=int(monthly_quota or 0),
        monthly_used=int(monthly_used or 0),
        monthly_remaining=monthly_remaining,
        concurrent_limit=int(concurrent_limit or 0),
        concurrent_active=int(concurrent_active or 0),
        quota_ok=monthly_ok and concurrent_ok,
        cost_score=cost_score,
        estimated_ai_cost_units=ai_units,
        recommendations=recommendations,
        blockers=blockers,
        guardrails=[
            "Cost Intelligence só recomenda; consumo real continua no Billing.",
            "Bloqueios reais de quota/crédito continuam nos serviços existentes.",
            "Produção cara deve exigir aprovação manual.",
        ],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
