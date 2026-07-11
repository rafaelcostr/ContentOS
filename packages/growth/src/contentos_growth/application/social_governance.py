"""Governance guardrails for social automation.

This module evaluates planned social operations before they reach Publisher,
Scheduler or Growth Execution. It creates an audit trail and blocks live actions
that do not satisfy explicit authorization, OAuth/provider readiness and policy
limits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal, Mapping

from contentos_growth.platform_registry import get_platform_profile, normalize_platform_id

GovernanceStatus = Literal["allowed", "review_required", "blocked"]


@dataclass(frozen=True)
class SocialAutomationPolicy:
    mode: str = "assisted"
    publish_authorized: bool = False
    live_publish_enabled: bool = False
    max_live_operations_per_run: int = 0
    max_operations_per_run: int = 30
    require_oauth_for_live: bool = True
    require_provider_for_live: bool = True
    require_human_review_for_live: bool = True
    allowed_platforms: tuple[str, ...] = ("youtube", "tiktok", "instagram")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | Any | None = None, **overrides: Any) -> "SocialAutomationPolicy":
        raw = dict(value or {}) if isinstance(value, Mapping) else {}
        raw.update({key: val for key, val in overrides.items() if val is not None})
        allowed = raw.get("allowed_platforms")
        if isinstance(allowed, str):
            allowed_platforms = tuple(normalize_platform_id(item.strip()) for item in allowed.split(",") if item.strip())
        elif isinstance(allowed, (list, tuple, set)):
            allowed_platforms = tuple(normalize_platform_id(str(item)) for item in allowed)
        else:
            allowed_platforms = cls.allowed_platforms
        return cls(
            mode=str(raw.get("mode") or "assisted"),
            publish_authorized=bool(raw.get("publish_authorized", False)),
            live_publish_enabled=bool(raw.get("live_publish_enabled", False)),
            max_live_operations_per_run=max(0, int(raw.get("max_live_operations_per_run", 0) or 0)),
            max_operations_per_run=max(1, int(raw.get("max_operations_per_run", 30) or 30)),
            require_oauth_for_live=bool(raw.get("require_oauth_for_live", True)),
            require_provider_for_live=bool(raw.get("require_provider_for_live", True)),
            require_human_review_for_live=bool(raw.get("require_human_review_for_live", True)),
            allowed_platforms=allowed_platforms,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "publish_authorized": self.publish_authorized,
            "live_publish_enabled": self.live_publish_enabled,
            "max_live_operations_per_run": self.max_live_operations_per_run,
            "max_operations_per_run": self.max_operations_per_run,
            "require_oauth_for_live": self.require_oauth_for_live,
            "require_provider_for_live": self.require_provider_for_live,
            "require_human_review_for_live": self.require_human_review_for_live,
            "allowed_platforms": list(self.allowed_platforms),
        }


@dataclass(frozen=True)
class SocialGovernanceDecision:
    operation_id: str
    operation_kind: str
    platform: str
    status: GovernanceStatus
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)
    audit_event: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation_kind": self.operation_kind,
            "platform": self.platform,
            "status": self.status,
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "required_actions": list(self.required_actions),
            "audit_event": dict(self.audit_event),
        }


@dataclass(frozen=True)
class SocialGovernanceReport:
    status: GovernanceStatus
    summary: str
    policy: SocialAutomationPolicy
    decisions: list[SocialGovernanceDecision] = field(default_factory=list)
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "policy": self.policy.to_dict(),
            "decisions": [decision.to_dict() for decision in self.decisions],
            "audit_log": [dict(item) for item in self.audit_log],
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _operation_id(project_id: str, operation: dict[str, Any]) -> str:
    raw = "|".join(
        [
            project_id,
            str(operation.get("kind") or "operation"),
            str(operation.get("platform") or "unknown"),
            str(operation.get("title") or ""),
            str(operation.get("calendar_item_id") or ""),
        ]
    )
    return sha256(raw.encode("utf-8")).hexdigest()[:16]


def _publish_mode(operation: dict[str, Any], policy: SocialAutomationPolicy) -> str:
    execution = _as_dict(operation.get("execution"))
    raw = str(execution.get("publish_mode") or operation.get("mode") or policy.mode or "assisted").lower()
    if raw in {"live", "automatic"}:
        return "live" if raw == "live" else "prepare_only"
    if raw in {"prepare", "prepare_only", "assisted"}:
        return "prepare_only"
    return "dry_run"


def evaluate_social_operation(
    *,
    project_id: str,
    operation: Mapping[str, Any] | Any,
    policy: SocialAutomationPolicy,
    live_operation_index: int = 0,
    actor_id: str | None = None,
    request_id: str | None = None,
) -> SocialGovernanceDecision:
    data = _as_dict(operation)
    platform = normalize_platform_id(str(data.get("platform") or "unknown"))
    publish_mode = _publish_mode(data, policy)
    execution = _as_dict(data.get("execution"))
    delegate = str(execution.get("delegate_to") or "").lower()
    profile = get_platform_profile(platform)
    reasons: list[str] = []
    required_actions: list[str] = []

    if platform not in policy.allowed_platforms:
        reasons.append("platform_not_allowed")
        required_actions.append("Adicionar plataforma à política de automação.")

    if len(data) == 0:
        reasons.append("invalid_operation")
        required_actions.append("Enviar uma operação social válida.")

    if data.get("block_reason"):
        reasons.append("operation_preblocked")
        required_actions.append(str(data.get("block_reason")))

    if publish_mode == "live":
        if not policy.live_publish_enabled:
            reasons.append("live_publish_disabled")
            required_actions.append("Ativar live_publish_enabled na política.")
        if not policy.publish_authorized:
            reasons.append("missing_explicit_authorization")
            required_actions.append("Enviar autorização explícita para publicação live.")
        if policy.max_live_operations_per_run <= 0 or live_operation_index >= policy.max_live_operations_per_run:
            reasons.append("live_operation_limit_exceeded")
            required_actions.append("Aumentar limite ou revisar fila live manualmente.")
        if policy.require_provider_for_live and (not profile or not profile.publish_supported):
            reasons.append("provider_publish_unsupported")
            required_actions.append("Configurar provider de publicação suportado.")
        if policy.require_oauth_for_live and not data.get("channel_id"):
            reasons.append("missing_oauth_channel")
            required_actions.append("Conectar OAuth do canal antes de publicar.")
        if policy.require_human_review_for_live:
            required_actions.append("Registrar aprovação humana antes de executar o Publisher.")

    if delegate == "publisher" and publish_mode == "live" and not data.get("can_execute"):
        reasons.append("publisher_execution_not_ready")
        required_actions.append("Resolver bloqueios do Publisher antes da execução.")

    if reasons:
        status: GovernanceStatus = "blocked"
        allowed = False
    elif publish_mode == "live" or policy.mode == "assisted":
        status = "review_required"
        allowed = publish_mode != "live"
    else:
        status = "allowed"
        allowed = True

    op_id = _operation_id(project_id, data)
    audit_event = {
        "event": "social_governance_decision",
        "operation_id": op_id,
        "project_id": project_id,
        "actor_id": actor_id,
        "request_id": request_id,
        "operation_kind": str(data.get("kind") or "operation"),
        "platform": platform,
        "publish_mode": publish_mode,
        "status": status,
        "allowed": allowed,
        "reasons": list(reasons),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return SocialGovernanceDecision(
        operation_id=op_id,
        operation_kind=str(data.get("kind") or "operation"),
        platform=platform,
        status=status,
        allowed=allowed,
        reasons=reasons,
        required_actions=required_actions,
        audit_event=audit_event,
    )


def evaluate_social_plan(
    *,
    project_id: str,
    operations: list[Mapping[str, Any] | Any],
    policy: SocialAutomationPolicy,
    actor_id: str | None = None,
    request_id: str | None = None,
) -> SocialGovernanceReport:
    limited = list(operations)[: policy.max_operations_per_run]
    decisions: list[SocialGovernanceDecision] = []
    live_count = 0
    for operation in limited:
        op_data = _as_dict(operation)
        publish_mode = _publish_mode(op_data, policy)
        decision = evaluate_social_operation(
            project_id=project_id,
            operation=op_data,
            policy=policy,
            live_operation_index=live_count,
            actor_id=actor_id,
            request_id=request_id,
        )
        decisions.append(decision)
        if publish_mode == "live":
            live_count += 1

    blocked = [decision for decision in decisions if decision.status == "blocked"]
    review = [decision for decision in decisions if decision.status == "review_required"]
    if blocked:
        status: GovernanceStatus = "blocked"
    elif review:
        status = "review_required"
    else:
        status = "allowed"

    summary = (
        f"Governança social {status}: {len(blocked)} bloqueio(s), "
        f"{len(review)} revisão(ões), {len(decisions)} decisão(ões)."
    )
    return SocialGovernanceReport(
        status=status,
        summary=summary,
        policy=policy,
        decisions=decisions,
        audit_log=[decision.audit_event for decision in decisions],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
