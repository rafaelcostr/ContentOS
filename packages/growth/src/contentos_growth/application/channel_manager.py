"""Channel Manager AI — daily channel agent (Growth OS Fase 15).

Reads analytics, learning, memory, competitors, calendar, trends and assets.
Decides actions; execution goes through Workflow Engine / Scheduler — never Celery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from contentos_growth.application.content_factory_bridge import prepare_calendar_dispatch
from contentos_growth.application.post_manager import is_text_content_type, is_video_content_type, plan_calendar_post
from contentos_growth.application.smart_scheduler_bridge import (
    build_growth_schedule_plan,
    can_schedule_calendar_item,
    normalize_scheduling_mode,
)
from contentos_growth.domain import GrowthRecommendation, GrowthStrategy
from contentos_growth.platform_registry import default_content_type, normalize_platform_id

ManagerActionKind = Literal["produce", "schedule", "generate_post", "recommend", "analyze"]
HealthStatus = Literal["healthy", "attention", "critical"]


@dataclass
class ChannelManagerSignals:
    channel_id: str
    project_id: str
    platform: str
    channel_name: str
    channel_score: float = 0.0
    has_credentials: bool = False
    overview: dict[str, Any] = field(default_factory=dict)
    channel_memory: dict[str, Any] = field(default_factory=dict)
    performance_rows: list[dict[str, Any]] = field(default_factory=list)
    competitors: list[dict[str, Any]] = field(default_factory=list)
    calendar_items: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    trend_brief: dict[str, Any] = field(default_factory=dict)
    posting_gap_days: float | None = None
    asset_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "platform": self.platform,
            "channel_name": self.channel_name,
            "channel_score": self.channel_score,
            "has_credentials": self.has_credentials,
            "overview_keys": list(self.overview.keys()),
            "memory_hooks": (self.channel_memory.get("top_hooks") or [])[:5],
            "performance_count": len(self.performance_rows),
            "competitor_count": len(self.competitors),
            "calendar_count": len(self.calendar_items),
            "recommendation_count": len(self.recommendations),
            "trend_score": self.trend_brief.get("trend_score"),
            "posting_gap_days": self.posting_gap_days,
            "asset_count": self.asset_count,
        }


@dataclass(frozen=True)
class ChannelManagerAction:
    action: ManagerActionKind
    title: str
    detail: str
    priority: str = "medium"
    calendar_item_id: str | None = None
    can_execute: bool = False
    block_reason: str | None = None
    execution: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "title": self.title,
            "detail": self.detail,
            "priority": self.priority,
            "calendar_item_id": self.calendar_item_id,
            "can_execute": self.can_execute,
            "block_reason": self.block_reason,
            "execution": dict(self.execution),
        }


@dataclass(frozen=True)
class ChannelDailyPlan:
    channel_id: str
    project_id: str
    platform: str
    channel_name: str
    summary: str
    health_status: HealthStatus
    focus_topics: list[str] = field(default_factory=list)
    actions: list[ChannelManagerAction] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    signals_summary: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "platform": self.platform,
            "channel_name": self.channel_name,
            "summary": self.summary,
            "health_status": self.health_status,
            "focus_topics": list(self.focus_topics),
            "actions": [action.to_dict() for action in self.actions],
            "opportunities": list(self.opportunities),
            "risks": list(self.risks),
            "signals_summary": dict(self.signals_summary),
            "generated_at": self.generated_at,
        }


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _calendar_channel_id(item: dict[str, Any]) -> str | None:
    metadata = item.get("metadata") or {}
    raw = item.get("channel_id") or metadata.get("channel_id")
    return str(raw) if raw else None


def _calendar_content_type(item: dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    platform = normalize_platform_id(str(metadata.get("platform") or "youtube"))
    return str(metadata.get("content_type") or default_content_type(platform)).lower()


def _infer_health_status(signals: ChannelManagerSignals) -> HealthStatus:
    if not signals.has_credentials or (signals.channel_score and signals.channel_score < 40):
        return "critical"
    gap = signals.posting_gap_days
    low_perf = sum(1 for row in signals.performance_rows if row.get("performance_tier") == "low")
    if (gap is not None and gap > 14) or low_perf >= 3 or (signals.channel_score and signals.channel_score < 55):
        return "critical"
    if (gap is not None and gap > 7) or low_perf >= 1 or (signals.channel_score and signals.channel_score < 70):
        return "attention"
    return "healthy"


def _collect_focus_topics(signals: ChannelManagerSignals) -> list[str]:
    topics: list[str] = []
    for hook in signals.channel_memory.get("top_hooks") or []:
        if hook and hook not in topics:
            topics.append(str(hook)[:120])
    for row in signals.performance_rows:
        if row.get("performance_tier") != "high":
            continue
        for candidate in (row.get("topic"), row.get("title")):
            if candidate and candidate not in topics:
                topics.append(str(candidate)[:120])
    for rec in signals.recommendations:
        title = rec.get("title") if isinstance(rec, dict) else getattr(rec, "title", None)
        if title and title not in topics:
            topics.append(str(title)[:120])
    for hook in signals.trend_brief.get("recommended_hooks") or []:
        if hook and hook not in topics:
            topics.append(str(hook)[:120])
    for pattern in signals.trend_brief.get("patterns") or []:
        if pattern and pattern not in topics:
            topics.append(str(pattern)[:120])
    return topics[:8]


def _filter_upcoming_calendar(items: list[dict[str, Any]], *, horizon_days: int = 7) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=horizon_days)
    upcoming: list[tuple[datetime, dict[str, Any]]] = []
    for item in items:
        if item.get("status") not in ("planned", "post_ready"):
            continue
        planned = _parse_datetime(item.get("planned_for"))
        if planned and planned <= cutoff:
            upcoming.append((planned, item))
    upcoming.sort(key=lambda pair: pair[0])
    return [item for _, item in upcoming]


def build_channel_daily_plan(
    signals: ChannelManagerSignals,
    *,
    strategy: GrowthStrategy | None = None,
    scheduling_mode: str = "assisted",
    horizon_days: int = 7,
) -> ChannelDailyPlan:
    """Pure decision layer — no I/O, no Celery."""
    mode = normalize_scheduling_mode(scheduling_mode)
    health = _infer_health_status(signals)
    focus_topics = _collect_focus_topics(signals)
    opportunities: list[str] = []
    risks: list[str] = []
    actions: list[ChannelManagerAction] = []

    platform_label = normalize_platform_id(signals.platform)
    upcoming = _filter_upcoming_calendar(signals.calendar_items, horizon_days=horizon_days)

    high_perf = [r for r in signals.performance_rows if r.get("performance_tier") == "high"]
    low_perf = [r for r in signals.performance_rows if r.get("performance_tier") == "low"]

    if high_perf:
        top = high_perf[0]
        title = top.get("title") or top.get("topic")
        if title:
            opportunities.append(f"Replicar formato vencedor: «{str(title)[:60]}»")
    if signals.competitors:
        opportunities.append(f"{len(signals.competitors)} concorrente(s) mapeados para benchmark de {platform_label}.")
    if focus_topics:
        opportunities.append(f"Tópico em foco: {focus_topics[0][:80]}")

    if not signals.has_credentials:
        risks.append("Canal sem OAuth — analytics e publicação limitados.")
    if signals.posting_gap_days is not None and signals.posting_gap_days > 7:
        risks.append(f"Gap de publicação: {signals.posting_gap_days:.0f} dias sem post.")
    if low_perf:
        risks.append(f"{len(low_perf)} mídia(s) com baixo desempenho nesta plataforma.")

    for item in upcoming[:5]:
        item_id = str(item.get("id") or "")
        topic = str(item.get("topic") or item.get("title") or "Conteúdo").strip()
        content_type = _calendar_content_type(item)

        if is_text_content_type(content_type):
            actions.append(
                ChannelManagerAction(
                    action="generate_post",
                    title=f"Gerar post: {topic[:50]}",
                    detail="Conteúdo de texto no calendário — delegar ao Multi Content.",
                    priority="high",
                    calendar_item_id=item_id or None,
                    can_execute=bool(item_id),
                )
            )
            continue

        if is_video_content_type(content_type):
            if mode == "automatic":
                actions.append(
                    ChannelManagerAction(
                        action="produce",
                        title=f"Produzir vídeo: {topic[:50]}",
                        detail="Item de vídeo no calendário — enviar ao Workflow Engine.",
                        priority="high",
                        calendar_item_id=item_id or None,
                        can_execute=bool(item_id),
                    )
                )
            else:
                can_sched, reason = can_schedule_calendar_item(item)
                actions.append(
                    ChannelManagerAction(
                        action="schedule",
                        title=f"Agendar produção: {topic[:50]}",
                        detail="Criar PipelineSchedule para execução assistida.",
                        priority="high",
                        calendar_item_id=item_id or None,
                        can_execute=can_sched and bool(item_id),
                        block_reason=None if can_sched else reason,
                    )
                )

    if not upcoming and (signals.posting_gap_days is None or signals.posting_gap_days >= 5):
        actions.append(
            ChannelManagerAction(
                action="recommend",
                title="Planejar conteúdo para os próximos dias",
                detail="Sem itens no calendário — gere estratégia em /growth/strategy ou adicione ao calendário.",
                priority="high" if (signals.posting_gap_days or 0) > 7 else "medium",
                can_execute=False,
            )
        )

    if signals.channel_score < 50 or not signals.overview:
        actions.append(
            ChannelManagerAction(
                action="analyze",
                title="Reanalisar canal",
                detail="Score baixo ou sem overview — sincronize OAuth e execute análise Growth.",
                priority="medium",
                can_execute=signals.has_credentials,
                block_reason=None if signals.has_credentials else "OAuth não conectado",
            )
        )

    if health == "healthy" and not actions:
        actions.append(
            ChannelManagerAction(
                action="recommend",
                title="Manter cadência atual",
                detail="Canal saudável — monitore performance e ajuste hooks conforme learning.",
                priority="low",
                can_execute=False,
            )
        )

    summary_parts = [
        f"Canal {signals.channel_name} ({platform_label})",
        f"saúde {health}",
    ]
    if upcoming:
        summary_parts.append(f"{len(upcoming)} item(ns) no calendário")
    summary_parts.append(f"{len(actions)} ação(ões) sugerida(s)")

    return ChannelDailyPlan(
        channel_id=signals.channel_id,
        project_id=signals.project_id,
        platform=platform_label,
        channel_name=signals.channel_name,
        summary=" · ".join(summary_parts),
        health_status=health,
        focus_topics=focus_topics,
        actions=actions,
        opportunities=opportunities,
        risks=risks,
        signals_summary=signals.to_dict(),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def enrich_channel_manager_actions(
    plan: ChannelDailyPlan,
    *,
    calendar_by_id: dict[str, dict[str, Any]],
    strategy: GrowthStrategy | None,
    scheduling_mode: str = "assisted",
    timezone: str = "UTC",
    workflow_name: str | None = None,
) -> ChannelDailyPlan:
    """Attach Workflow/Scheduler payloads — still no direct Celery."""
    mode = normalize_scheduling_mode(scheduling_mode)
    enriched: list[ChannelManagerAction] = []

    for action in plan.actions:
        execution: dict[str, Any] = {}
        if not action.calendar_item_id:
            enriched.append(action)
            continue

        item = calendar_by_id.get(action.calendar_item_id)
        if not item:
            enriched.append(
                ChannelManagerAction(
                    action=action.action,
                    title=action.title,
                    detail=action.detail,
                    priority=action.priority,
                    calendar_item_id=action.calendar_item_id,
                    can_execute=False,
                    block_reason="Item de calendário não encontrado",
                )
            )
            continue

        try:
            if action.action == "produce":
                dispatch = prepare_calendar_dispatch(
                    calendar_item=item,
                    strategy=strategy,
                    workflow_name=workflow_name,
                )
                execution = {
                    "type": "workflow",
                    "workflow_request": dispatch.to_workflow_request(auto_start=True),
                    "calendar_item_id": action.calendar_item_id,
                }
            elif action.action == "schedule":
                schedule_plan = build_growth_schedule_plan(
                    calendar_item=item,
                    strategy=strategy,
                    mode=mode,
                    timezone=timezone,
                    workflow_name=workflow_name,
                )
                execution = {
                    "type": "scheduler",
                    "schedule_plan": {
                        "project_id": schedule_plan.project_id,
                        "calendar_item_id": schedule_plan.calendar_item_id,
                        "name": schedule_plan.name,
                        "topic": schedule_plan.topic,
                        "cron_expression": schedule_plan.cron_expression,
                        "timezone": schedule_plan.timezone,
                        "workflow_name": schedule_plan.workflow_name,
                        "context_json": schedule_plan.context_json,
                        "mode": schedule_plan.mode,
                        "is_active": schedule_plan.is_active,
                    },
                }
            elif action.action == "generate_post":
                post_plan = plan_calendar_post(calendar_item=item, strategy=strategy)
                execution = {
                    "type": "multi_content",
                    "post_plan": {
                        "calendar_item_id": post_plan.calendar_item_id,
                        "project_id": post_plan.project_id,
                        "topic": post_plan.topic,
                        "platform": post_plan.platform,
                        "content_type": post_plan.content_type,
                        "mode": post_plan.mode,
                        "text_formats": list(post_plan.text_formats),
                        "payload": dict(post_plan.payload),
                    },
                }
        except ValueError as exc:
            enriched.append(
                ChannelManagerAction(
                    action=action.action,
                    title=action.title,
                    detail=action.detail,
                    priority=action.priority,
                    calendar_item_id=action.calendar_item_id,
                    can_execute=False,
                    block_reason=str(exc),
                )
            )
            continue

        enriched.append(
            ChannelManagerAction(
                action=action.action,
                title=action.title,
                detail=action.detail,
                priority=action.priority,
                calendar_item_id=action.calendar_item_id,
                can_execute=action.can_execute,
                block_reason=action.block_reason,
                execution=execution,
            )
        )

    return ChannelDailyPlan(
        channel_id=plan.channel_id,
        project_id=plan.project_id,
        platform=plan.platform,
        channel_name=plan.channel_name,
        summary=plan.summary,
        health_status=plan.health_status,
        focus_topics=plan.focus_topics,
        actions=enriched,
        opportunities=plan.opportunities,
        risks=plan.risks,
        signals_summary=plan.signals_summary,
        generated_at=plan.generated_at,
    )


def filter_calendar_for_channel(items: list[dict[str, Any]], channel_id: str) -> list[dict[str, Any]]:
    return [item for item in items if _calendar_channel_id(item) == channel_id]


def filter_performance_for_platform(rows: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    normalized = normalize_platform_id(platform)
    return [row for row in rows if normalize_platform_id(str(row.get("platform") or "")) == normalized]


def filter_competitors_for_platform(competitors: list[Any], platform: str) -> list[dict[str, Any]]:
    normalized = normalize_platform_id(platform)
    result: list[dict[str, Any]] = []
    for competitor in competitors:
        data = competitor.to_dict() if hasattr(competitor, "to_dict") else dict(competitor)
        if normalize_platform_id(str(data.get("platform") or "")) == normalized:
            result.append(data)
    return result


def recommendations_to_dicts(recommendations: list[GrowthRecommendation]) -> list[dict[str, Any]]:
    return [rec.to_dict() for rec in recommendations]
