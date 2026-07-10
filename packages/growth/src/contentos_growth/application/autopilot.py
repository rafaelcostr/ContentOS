"""Growth Autopilot control-plane status.

This module is intentionally pure: it does not execute workflows, publish posts,
or mutate calendar state. It summarizes whether the closed-loop Growth cycle can
run and what is blocking it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from contentos_growth.application.channel_manager import ChannelDailyPlan
from contentos_growth.domain import ChannelProfile, GrowthRecommendation, GrowthStrategy

AutopilotStageStatus = Literal["ready", "partial", "blocked"]
AutopilotMode = Literal["manual", "assisted", "automatic"]


@dataclass(frozen=True)
class AutopilotStage:
    key: str
    label: str
    status: AutopilotStageStatus
    detail: str
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "detail": self.detail,
            "blockers": list(self.blockers),
            "next_actions": list(self.next_actions),
        }


@dataclass(frozen=True)
class AutopilotChannelStatus:
    channel_id: str
    platform: str
    name: str
    score: float
    has_credentials: bool
    health_status: str
    planned_actions: int
    executable_actions: int
    blockers: list[str] = field(default_factory=list)
    next_actions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "platform": self.platform,
            "name": self.name,
            "score": self.score,
            "has_credentials": self.has_credentials,
            "health_status": self.health_status,
            "planned_actions": self.planned_actions,
            "executable_actions": self.executable_actions,
            "blockers": list(self.blockers),
            "next_actions": [dict(action) for action in self.next_actions],
        }


@dataclass(frozen=True)
class GrowthAutopilotStatus:
    project_id: str
    mode: AutopilotMode
    status: AutopilotStageStatus
    summary: str
    score: int
    generated_at: str
    stages: list[AutopilotStage] = field(default_factory=list)
    channels: list[AutopilotChannelStatus] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "mode": self.mode,
            "status": self.status,
            "summary": self.summary,
            "score": self.score,
            "generated_at": self.generated_at,
            "stages": [stage.to_dict() for stage in self.stages],
            "channels": [channel.to_dict() for channel in self.channels],
            "blockers": list(self.blockers),
            "next_actions": list(self.next_actions),
        }


def _stage_status(*, ok: bool, partial: bool = False) -> AutopilotStageStatus:
    if ok:
        return "ready"
    return "partial" if partial else "blocked"


def _planned_calendar_items(calendar_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in calendar_items if item.get("status") in {"planned", "post_ready", "scheduled"}]


def _channel_status(channel: ChannelProfile, plan: ChannelDailyPlan | None) -> AutopilotChannelStatus:
    blockers: list[str] = []
    if not channel.has_credentials:
        blockers.append("OAuth/perfil real não conectado")
    if channel.score and channel.score < 50:
        blockers.append("Score do canal abaixo de 50")
    if plan and plan.risks:
        blockers.extend(plan.risks[:3])

    actions = [action.to_dict() for action in plan.actions] if plan else []
    executable = [action for action in actions if action.get("can_execute")]

    return AutopilotChannelStatus(
        channel_id=channel.channel_id,
        platform=channel.platform,
        name=channel.name,
        score=channel.score,
        has_credentials=channel.has_credentials,
        health_status=plan.health_status if plan else "unknown",
        planned_actions=len(actions),
        executable_actions=len(executable),
        blockers=blockers,
        next_actions=actions[:5],
    )


def build_growth_autopilot_status(
    *,
    project_id: str,
    channels: list[ChannelProfile],
    calendar_items: list[dict[str, Any]],
    recommendations: list[GrowthRecommendation],
    strategy: GrowthStrategy | None,
    channel_plans: dict[str, ChannelDailyPlan],
    readiness: dict[str, Any] | None = None,
    mode: str = "assisted",
) -> GrowthAutopilotStatus:
    """Build a single control-plane report for the closed-loop Growth cycle."""
    normalized_mode: AutopilotMode = "automatic" if mode == "automatic" else "manual" if mode == "manual" else "assisted"
    planned_items = _planned_calendar_items(calendar_items)
    connected_channels = [channel for channel in channels if channel.has_credentials]
    active_channels = [channel for channel in channels if channel.is_active]
    channel_statuses = [_channel_status(channel, channel_plans.get(channel.channel_id)) for channel in active_channels]

    readiness_status = str((readiness or {}).get("status") or "blocked")
    readiness_blocked = readiness_status == "blocked"

    stages = [
        AutopilotStage(
            key="connect_accounts",
            label="Conectar perfis",
            status=_stage_status(ok=bool(connected_channels), partial=bool(channels)),
            detail=f"{len(connected_channels)}/{len(channels)} canal(is) com credenciais.",
            blockers=[] if connected_channels else ["Conecte pelo menos um canal real via OAuth."],
            next_actions=["Conectar YouTube/TikTok/Instagram em Canais/Publicação."],
        ),
        AutopilotStage(
            key="understand_channel",
            label="Entender canal e público",
            status=_stage_status(ok=any(channel.score > 0 for channel in channels), partial=bool(channels)),
            detail="Usa Channel Analyzer, Channel Memory, Brand Intelligence e Project DNA.",
            blockers=[] if any(channel.score > 0 for channel in channels) else ["Execute análise do canal para criar score/perfil."],
            next_actions=["Rodar análise Growth nos canais conectados."],
        ),
        AutopilotStage(
            key="strategy",
            label="Criar estratégia",
            status=_stage_status(ok=strategy is not None, partial=bool(recommendations)),
            detail="Estratégia Growth ativa, recomendações e posicionamento por projeto/canal.",
            blockers=[] if strategy else ["Gere uma estratégia Growth para o projeto."],
            next_actions=["Gerar estratégia em Growth Strategy."],
        ),
        AutopilotStage(
            key="calendar",
            label="Criar calendário",
            status=_stage_status(ok=bool(planned_items), partial=bool(calendar_items)),
            detail=f"{len(planned_items)} item(ns) planejados/agendados.",
            blockers=[] if planned_items else ["Crie ou gere calendário editorial Growth."],
            next_actions=["Gerar calendário a partir da estratégia."],
        ),
        AutopilotStage(
            key="daily_decision",
            label="Decidir o que fazer hoje",
            status=_stage_status(ok=any(ch.executable_actions for ch in channel_statuses), partial=bool(channel_statuses)),
            detail="Channel Manager transforma sinais em ações de produzir, agendar, gerar post ou analisar.",
            blockers=[] if any(ch.executable_actions for ch in channel_statuses) else ["Nenhuma ação executável encontrada hoje."],
            next_actions=["Executar Channel Manager em dry-run e aprovar ações."],
        ),
        AutopilotStage(
            key="produce_publish",
            label="Produzir e publicar",
            status="partial" if planned_items else "blocked",
            detail="Produção usa factory-full/v5; publicação real depende de OAuth, QA e PUBLISH_MODE.",
            blockers=["Publicação real exige credenciais/permissões e PUBLISH_MODE adequado."] if readiness_blocked else [],
            next_actions=["Produzir itens planejados e publicar primeiro em dry_run/prepare_only."],
        ),
        AutopilotStage(
            key="learn_loop",
            label="Acompanhar, aprender e melhorar",
            status=_stage_status(ok=bool(recommendations), partial=bool(channels)),
            detail="Usa Analytics, Performance Learning, Learning Engine, Knowledge Base e Creative Memory.",
            blockers=[] if recommendations else ["Sincronize performance real para alimentar recomendações."],
            next_actions=["Sincronizar analytics e performance após publicações."],
        ),
    ]

    blockers: list[str] = []
    for stage in stages:
        if stage.status == "blocked":
            blockers.extend(stage.blockers)
    for channel in channel_statuses:
        blockers.extend(channel.blockers[:2])
    if readiness_blocked:
        blockers.append("Growth/OAuth readiness ainda está bloqueado por credenciais externas.")

    ready_count = sum(1 for stage in stages if stage.status == "ready")
    partial_count = sum(1 for stage in stages if stage.status == "partial")
    score = int(round(((ready_count * 100) + (partial_count * 50)) / max(len(stages), 1)))
    status: AutopilotStageStatus = "ready" if score >= 90 and not blockers else "partial" if score >= 40 else "blocked"

    next_actions: list[str] = []
    for stage in stages:
        for action in stage.next_actions:
            if action not in next_actions:
                next_actions.append(action)
    if normalized_mode != "automatic":
        next_actions.append("Manter modo assistido até validar OAuth, qualidade e publicação real.")

    return GrowthAutopilotStatus(
        project_id=project_id,
        mode=normalized_mode,
        status=status,
        summary=f"Autopilot Growth {status}: {ready_count}/{len(stages)} etapas prontas, score {score}/100.",
        score=score,
        generated_at=datetime.now(timezone.utc).isoformat(),
        stages=stages,
        channels=channel_statuses,
        blockers=list(dict.fromkeys(blockers)),
        next_actions=next_actions[:10],
    )
