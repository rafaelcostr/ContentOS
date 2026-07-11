"""Social Autopilot planner.

Plans social operations using existing Publisher, Scheduler, Platform Analytics,
Calendar and Growth Execution contracts. It never publishes live content by
itself; live operations require OAuth, provider support and explicit approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from contentos_growth.application.social_governance import SocialAutomationPolicy, evaluate_social_plan
from contentos_growth.platform_registry import get_platform_profile, normalize_platform_id

SocialOperationKind = Literal[
    "repost",
    "crosspost",
    "story",
    "thread",
    "community_post",
    "continuation",
    "clip",
    "derived_video",
]
SocialPlanStatus = Literal["ready", "assisted", "blocked"]


@dataclass(frozen=True)
class SocialOperation:
    kind: SocialOperationKind
    title: str
    detail: str
    platform: str
    channel_id: str | None = None
    calendar_item_id: str | None = None
    priority: str = "medium"
    mode: str = "assisted"
    can_execute: bool = False
    block_reason: str | None = None
    execution: dict[str, Any] = field(default_factory=dict)
    guardrails: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "detail": self.detail,
            "platform": self.platform,
            "channel_id": self.channel_id,
            "calendar_item_id": self.calendar_item_id,
            "priority": self.priority,
            "mode": self.mode,
            "can_execute": self.can_execute,
            "block_reason": self.block_reason,
            "execution": dict(self.execution),
            "guardrails": list(self.guardrails),
        }


@dataclass(frozen=True)
class SocialAutopilotPlan:
    project_id: str
    mode: str
    status: SocialPlanStatus
    summary: str
    operations: list[SocialOperation] = field(default_factory=list)
    blocked_operations: list[SocialOperation] = field(default_factory=list)
    publisher_contract: dict[str, Any] = field(default_factory=dict)
    scheduler_contract: dict[str, Any] = field(default_factory=dict)
    governance_contract: dict[str, Any] = field(default_factory=dict)
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "mode": self.mode,
            "status": self.status,
            "summary": self.summary,
            "operations": [item.to_dict() for item in self.operations],
            "blocked_operations": [item.to_dict() for item in self.blocked_operations],
            "publisher_contract": dict(self.publisher_contract),
            "scheduler_contract": dict(self.scheduler_contract),
            "governance_contract": dict(self.governance_contract),
            "audit_log": [dict(item) for item in self.audit_log],
            "guardrails": list(self.guardrails),
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


def _priority_rank(priority: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 2)


def _title(item: dict[str, Any]) -> str:
    return str(item.get("title") or item.get("topic") or "Conteúdo social").strip()[:160]


def _channel_for_platform(channels: list[dict[str, Any]], platform: str) -> dict[str, Any] | None:
    normalized = normalize_platform_id(platform)
    return next((channel for channel in channels if normalize_platform_id(str(channel.get("platform"))) == normalized), None)


def _execution_contract(kind: str, *, platform: str, calendar_item_id: str | None, mode: str) -> dict[str, Any]:
    if kind in {"story", "thread", "community_post"}:
        return {
            "type": "publisher",
            "delegate_to": "Publisher",
            "publish_mode": "prepare_only" if mode != "live" else "live",
            "calendar_item_id": calendar_item_id,
        }
    if kind in {"repost", "crosspost"}:
        return {
            "type": "publisher",
            "delegate_to": "Publisher",
            "publish_mode": "prepare_only" if mode != "live" else "live",
            "target_platform": platform,
            "calendar_item_id": calendar_item_id,
        }
    return {
        "type": "growth_execution",
        "delegate_to": "Growth Execution",
        "next_step": "produce" if kind in {"clip", "derived_video", "continuation"} else "prepare",
        "calendar_item_id": calendar_item_id,
    }


def _is_live_allowed(channel: dict[str, Any] | None, platform: str, mode: str, publish_authorized: bool) -> tuple[bool, str | None]:
    profile = get_platform_profile(platform)
    if mode != "live":
        return True, None
    if not publish_authorized:
        return False, "Publicação live exige autorização explícita."
    if not profile or not profile.publish_supported:
        return False, "Provider da plataforma não suporta publicação live."
    if not channel or not bool(channel.get("has_credentials")):
        return False, "OAuth/credenciais do canal são obrigatórios para publicação live."
    return True, None


def _operation(
    *,
    kind: SocialOperationKind,
    title: str,
    detail: str,
    platform: str,
    channel: dict[str, Any] | None,
    calendar_item_id: str | None,
    priority: str,
    mode: str,
    publish_authorized: bool,
) -> SocialOperation:
    allowed, reason = _is_live_allowed(channel, platform, mode, publish_authorized)
    execution = _execution_contract(kind, platform=platform, calendar_item_id=calendar_item_id, mode=mode)
    return SocialOperation(
        kind=kind,
        title=title,
        detail=detail,
        platform=platform,
        channel_id=str(channel.get("channel_id")) if channel and channel.get("channel_id") else None,
        calendar_item_id=calendar_item_id,
        priority=priority,
        mode=mode,
        can_execute=allowed and mode in {"assisted", "automatic", "live"},
        block_reason=reason,
        execution=execution,
        guardrails=[
            "Modo padrão assistido.",
            "Publisher existente executa preparação/publicação quando autorizado.",
            "Scheduler existente agenda operações; este plano não cria scheduler paralelo.",
        ],
    )


def build_social_autopilot_plan(
    *,
    project_id: str,
    channels: list[Mapping[str, Any] | Any] | None = None,
    calendar_items: list[Mapping[str, Any] | Any] | None = None,
    performance_rows: list[Mapping[str, Any] | Any] | None = None,
    community_signals: Mapping[str, Any] | Any | None = None,
    mode: str = "assisted",
    publish_authorized: bool = False,
    max_operations: int = 8,
    automation_policy: Mapping[str, Any] | Any | None = None,
    actor_id: str | None = None,
    request_id: str | None = None,
) -> SocialAutopilotPlan:
    normalized_mode = "assisted" if mode in {"auto", "assistido", ""} else mode
    channel_data = [_as_dict(item) for item in channels or []]
    calendar = [_as_dict(item) for item in calendar_items or []]
    performance = [_as_dict(item) for item in performance_rows or []]
    community = _as_dict(community_signals or {})
    operations: list[SocialOperation] = []

    for item in calendar[: max_operations * 2]:
        metadata = _as_dict(item.get("metadata"))
        platform = normalize_platform_id(str(metadata.get("platform") or item.get("platform") or "youtube"))
        channel = _channel_for_platform(channel_data, platform)
        calendar_item_id = str(item.get("id")) if item.get("id") else None
        base_title = _title(item)
        content_type = str(metadata.get("content_type") or "short").lower()
        if content_type in {"short", "video", "reel", "content"}:
            operations.append(
                _operation(
                    kind="clip",
                    title=f"Criar clipe social: {base_title}",
                    detail="Transformar o item do calendário em corte curto para distribuição social.",
                    platform=platform,
                    channel=channel,
                    calendar_item_id=calendar_item_id,
                    priority="high" if item.get("status") in {"post_ready", "scheduled"} else "medium",
                    mode=normalized_mode,
                    publish_authorized=publish_authorized,
                )
            )
            operations.append(
                _operation(
                    kind="crosspost",
                    title=f"Preparar crosspost: {base_title}",
                    detail="Adaptar criativo/legenda para republicação em plataforma compatível.",
                    platform=platform,
                    channel=channel,
                    calendar_item_id=calendar_item_id,
                    priority="medium",
                    mode=normalized_mode,
                    publish_authorized=publish_authorized,
                )
            )
            operations.append(
                _operation(
                    kind="story",
                    title=f"Story de apoio: {base_title}",
                    detail="Preparar story curto para reforçar a distribuição do conteúdo principal.",
                    platform=platform,
                    channel=channel,
                    calendar_item_id=calendar_item_id,
                    priority="medium",
                    mode=normalized_mode,
                    publish_authorized=publish_authorized,
                )
            )
        else:
            operations.append(
                _operation(
                    kind="thread",
                    title=f"Gerar thread/post: {base_title}",
                    detail="Converter o tema em sequência textual ou post social preparado para revisão.",
                    platform=platform,
                    channel=channel,
                    calendar_item_id=calendar_item_id,
                    priority="medium",
                    mode=normalized_mode,
                    publish_authorized=publish_authorized,
                )
            )

    for row in performance[:4]:
        title = str(row.get("title") or row.get("topic") or "conteúdo com bom desempenho").strip()[:160]
        platform = normalize_platform_id(str(row.get("platform") or "youtube"))
        channel = _channel_for_platform(channel_data, platform)
        tier = str(row.get("performance_tier") or "").lower()
        if tier == "high" or float(row.get("views") or 0) >= 1000:
            operations.append(
                _operation(
                    kind="repost",
                    title=f"Repostar vencedor: {title}",
                    detail="Reaproveitar conteúdo de alta performance com nova legenda/gancho.",
                    platform=platform,
                    channel=channel,
                    calendar_item_id=None,
                    priority="high",
                    mode=normalized_mode,
                    publish_authorized=publish_authorized,
                )
            )
            operations.append(
                _operation(
                    kind="derived_video",
                    title=f"Vídeo derivado: {title}",
                    detail="Criar nova variação baseada em aprendizado de performance.",
                    platform=platform,
                    channel=channel,
                    calendar_item_id=None,
                    priority="high",
                    mode=normalized_mode,
                    publish_authorized=publish_authorized,
                )
            )
            operations.append(
                _operation(
                    kind="continuation",
                    title=f"Continuação: {title}",
                    detail="Planejar uma parte 2 ou sequência para aproveitar o interesse já validado.",
                    platform=platform,
                    channel=channel,
                    calendar_item_id=None,
                    priority="high",
                    mode=normalized_mode,
                    publish_authorized=publish_authorized,
                )
            )

    for signal in _as_list(community.get("video_ideas"))[:3]:
        raw = _as_dict(signal)
        platform = normalize_platform_id(str(raw.get("platform") or "youtube"))
        channel = _channel_for_platform(channel_data, platform)
        operations.append(
            _operation(
                kind="community_post",
                title=str(raw.get("title") or "Post da comunidade")[:160],
                detail=str(raw.get("detail") or "Transformar sinal da comunidade em post social."),
                platform=platform,
                channel=channel,
                calendar_item_id=None,
                priority=str(raw.get("priority") or "medium"),
                mode=normalized_mode,
                publish_authorized=publish_authorized,
            )
        )

    if not operations and channel_data:
        channel = channel_data[0]
        platform = normalize_platform_id(str(channel.get("platform") or "youtube"))
        operations.append(
            _operation(
                kind="story",
                title="Story de presença do canal",
                detail="Preparar story/post leve para manter cadência social.",
                platform=platform,
                channel=channel,
                calendar_item_id=None,
                priority="low",
                mode=normalized_mode,
                publish_authorized=publish_authorized,
            )
        )

    operations.sort(key=lambda item: (_priority_rank(item.priority), item.platform, item.title))
    limited = operations[: max(1, max_operations)]
    policy = SocialAutomationPolicy.from_mapping(
        automation_policy,
        mode=normalized_mode,
        publish_authorized=publish_authorized,
        live_publish_enabled=normalized_mode == "live" and publish_authorized,
        max_live_operations_per_run=max_operations if normalized_mode == "live" and publish_authorized else 0,
        max_operations_per_run=max_operations,
    )
    governance = evaluate_social_plan(
        project_id=project_id,
        operations=[item.to_dict() for item in limited],
        policy=policy,
        actor_id=actor_id,
        request_id=request_id,
    )
    ready = [item for item in limited if item.can_execute and not item.block_reason]
    blocked = [item for item in limited if item.block_reason]
    if normalized_mode == "live" and (blocked or governance.status == "blocked"):
        status: SocialPlanStatus = "blocked"
    elif ready:
        status = "ready" if normalized_mode in {"automatic", "live"} else "assisted"
    else:
        status = "assisted"

    summary = (
        f"Social Autopilot {status}: {len(ready)} operação(ões) pronta(s), "
        f"{len(blocked)} bloqueada(s), modo {normalized_mode}."
    )
    return SocialAutopilotPlan(
        project_id=project_id,
        mode=normalized_mode or "assisted",
        status=status,
        summary=summary,
        operations=ready if normalized_mode == "live" else limited,
        blocked_operations=blocked,
        publisher_contract={
            "uses_existing_publisher": True,
            "live_requires_oauth": True,
            "live_requires_provider": True,
            "live_requires_authorization": True,
        },
        scheduler_contract={
            "uses_existing_scheduler": True,
            "creates_scheduler_engine": False,
        },
        governance_contract=governance.to_dict(),
        audit_log=governance.audit_log,
        guardrails=[
            "Modo padrão assistido; revisão humana antes de live publish.",
            "Publicação live exige OAuth, provider suportado e autorização explícita.",
            "Plano usa Publisher, Scheduler, Calendar e Growth Execution existentes.",
            "Governança registra decisões e bloqueia live publish fora da política.",
        ],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )



