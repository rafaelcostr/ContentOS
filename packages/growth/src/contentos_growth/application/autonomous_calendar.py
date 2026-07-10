"""Autonomous calendar planner for Growth Autopilot.

This module is pure: it reads channel intelligence and existing calendar
signals, then proposes missing slots without mutating stored data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha1
from typing import Any

from contentos_growth.application.channel_intelligence import ChannelIntelligenceSnapshot
from contentos_growth.domain import GrowthStrategy
from contentos_growth.platform_registry import default_content_type, get_platform_profile, normalize_platform_id


@dataclass(frozen=True)
class AutonomousCalendarSlot:
    channel_id: str | None
    platform: str
    title: str
    topic: str
    planned_for: str
    content_type: str
    source_signals: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_calendar_item(self, project_id: str) -> dict[str, Any]:
        return {
            "project_id": project_id,
            "channel_id": self.channel_id,
            "title": self.title,
            "topic": self.topic,
            "planned_for": self.planned_for,
            "status": "planned",
            "metadata": {
                **dict(self.metadata),
                "platform": normalize_platform_id(self.platform),
                "content_type": self.content_type,
                "source": "autonomous_calendar",
                "source_signals": list(self.source_signals),
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "platform": normalize_platform_id(self.platform),
            "title": self.title,
            "topic": self.topic,
            "planned_for": self.planned_for,
            "content_type": self.content_type,
            "source_signals": list(self.source_signals),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AutonomousCalendarPlan:
    project_id: str
    horizon_days: int
    mode: str
    status: str
    summary: str
    existing_items: int
    proposed_items: list[AutonomousCalendarSlot] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_calendar_items(self) -> list[dict[str, Any]]:
        return [slot.to_calendar_item(self.project_id) for slot in self.proposed_items]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "horizon_days": self.horizon_days,
            "mode": self.mode,
            "status": self.status,
            "summary": self.summary,
            "existing_items": self.existing_items,
            "proposed_items": [slot.to_dict() for slot in self.proposed_items],
            "calendar_items": self.to_calendar_items(),
            "gaps": list(self.gaps),
            "risks": list(self.risks),
            "generated_at": self.generated_at,
        }


def _unique(items: list[Any], *, limit: int = 20) -> list[str]:
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


def _existing_keys(calendar_items: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for item in calendar_items:
        title = str(item.get("title") or "").strip().lower()
        topic = str(item.get("topic") or "").strip().lower()
        if title:
            keys.add(title)
        if topic:
            keys.add(topic)
    return keys


def _weekly_posts(snapshot: ChannelIntelligenceSnapshot, strategy: GrowthStrategy | None) -> int:
    cadence = strategy.cadence if strategy else {}
    raw = snapshot.posting_intelligence.get("strategy_weekly_posts") or cadence.get("weekly_posts")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        profile = get_platform_profile(snapshot.platform)
        value = profile.weekly_posts_default if profile else 3
    return max(1, min(value, 14))


def _posting_hours(snapshot: ChannelIntelligenceSnapshot, strategy: GrowthStrategy | None) -> list[int]:
    values = [
        *list(snapshot.posting_intelligence.get("best_posting_hours") or []),
        *list((strategy.cadence.get("posting_hours") if strategy else []) or []),
    ]
    hours: list[int] = []
    for value in values:
        try:
            hour = int(value)
        except (TypeError, ValueError):
            continue
        if 0 <= hour <= 23 and hour not in hours:
            hours.append(hour)
    return hours[:6] or [12, 18, 20]


def _topics(snapshot: ChannelIntelligenceSnapshot, strategy: GrowthStrategy | None) -> list[tuple[str, list[str]]]:
    patterns = snapshot.content_patterns or {}
    historical = snapshot.historical_videos or {}
    strategy_goals = list(strategy.goals if strategy else [])
    raw_topics = [
        *list(patterns.get("top_themes") or []),
        *list(snapshot.opportunities or []),
        *[row.get("title") for row in historical.get("winning_videos") or [] if isinstance(row, dict)],
        *list(historical.get("winning_titles") or []),
        *strategy_goals,
        snapshot.niche,
    ]
    topics = _unique(raw_topics, limit=24)
    if not topics:
        topics = [
            f"O que postar hoje em {snapshot.name}",
            f"Hook de curiosidade para {snapshot.platform}",
            "Conteudo de valor para aquecer a audiencia",
        ]
    return [(topic, _source_signals(topic, snapshot)) for topic in topics]


def _source_signals(topic: str, snapshot: ChannelIntelligenceSnapshot) -> list[str]:
    signals = ["channel_intelligence"]
    if topic in (snapshot.content_patterns or {}).get("top_themes", []):
        signals.append("top_themes")
    if topic in snapshot.opportunities:
        signals.append("opportunities")
    if topic == snapshot.niche:
        signals.append("niche")
    if (snapshot.historical_videos or {}).get("winning_titles"):
        signals.append("historical_performance")
    if (snapshot.competitor_intelligence or {}).get("competitors"):
        signals.append("competitors")
    return _unique(signals, limit=8)


def _planned_datetime(start: datetime, index: int, total: int, hours: list[int], horizon_days: int) -> datetime:
    spacing = max(1, horizon_days // max(total, 1))
    day_offset = min(index * spacing, max(horizon_days - 1, 0))
    hour = hours[index % len(hours)]
    return (start + timedelta(days=day_offset)).replace(hour=hour, minute=0, second=0, microsecond=0)


def _objective_metadata(topic: str, snapshot: ChannelIntelligenceSnapshot, strategy: GrowthStrategy | None) -> dict[str, Any]:
    goals = list(strategy.goals if strategy else [])
    positioning = (strategy.positioning if strategy else "") or snapshot.niche or "Crescer o canal com conteudo consistente"
    matched_goal = next((goal for goal in goals if str(goal).lower() in topic.lower()), None)
    objective_title = str(matched_goal or goals[0] if goals else positioning)
    objective_key = f"{snapshot.project_id}:{snapshot.channel_id}:{objective_title}:{topic}"
    objective_id = sha1(objective_key.encode("utf-8")).hexdigest()[:12]
    return {
        "objective_id": f"obj-{objective_id}",
        "objective_title": objective_title[:200],
        "objective_level": "content",
        "objective_path": [
            f"Projeto: {snapshot.project_id}",
            f"Canal: {snapshot.name}",
            f"Estrategia: {objective_title[:120]}",
            f"Conteudo: {topic[:120]}",
        ],
        "objective_source": "growth_strategy" if strategy else "channel_intelligence",
        "objective_status": "linked",
    }


def build_autonomous_calendar_plan(
    *,
    project_id: str,
    snapshots: list[ChannelIntelligenceSnapshot],
    existing_calendar: list[dict[str, Any]],
    strategy: GrowthStrategy | None = None,
    horizon_days: int = 30,
    mode: str = "draft",
    max_items: int = 20,
) -> AutonomousCalendarPlan:
    existing_count = len(existing_calendar)
    gaps: list[str] = []
    risks: list[str] = []

    if not snapshots:
        return AutonomousCalendarPlan(
            project_id=project_id,
            horizon_days=horizon_days,
            mode=mode,
            status="blocked",
            summary="Nenhum canal disponivel para planejar o calendario autonomo.",
            existing_items=existing_count,
            gaps=["Conecte ou cadastre pelo menos um canal."],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    if any(snapshot.confidence == "low" for snapshot in snapshots):
        risks.append("Um ou mais canais ainda tem baixa confianca de inteligencia.")

    start = datetime.now(timezone.utc) + timedelta(days=1)
    existing = _existing_keys(existing_calendar)
    proposed: list[AutonomousCalendarSlot] = []

    for snapshot in snapshots:
        weekly = _weekly_posts(snapshot, strategy)
        target = max(1, round(weekly * (horizon_days / 7)))
        target = min(target, max_items)
        needed = max(0, target - existing_count)
        if needed <= 0:
            continue

        topics = _topics(snapshot, strategy)
        hours = _posting_hours(snapshot, strategy)
        for topic, source_signals in topics:
            if len(proposed) >= max_items or needed <= 0:
                break
            key = topic.lower()
            if key in existing:
                continue
            index = len(proposed)
            content_type = default_content_type(snapshot.platform, index)
            planned = _planned_datetime(start, index, max(target, 1), hours, horizon_days)
            title = topic[:120]
            proposed.append(
                AutonomousCalendarSlot(
                    channel_id=snapshot.channel_id,
                    platform=snapshot.platform,
                    title=title,
                    topic=topic,
                    planned_for=planned.isoformat(),
                    content_type=content_type,
                    source_signals=source_signals,
                    metadata={
                        "channel_name": snapshot.name,
                        "intelligence_confidence": snapshot.confidence,
                        "intelligence_score": snapshot.score,
                        "autopilot_mode": mode,
                        **_objective_metadata(topic, snapshot, strategy),
                    },
                )
            )
            existing.add(key)
            needed -= 1

    if not proposed:
        gaps.append("Calendario atual ja cobre a cadencia estimada ou faltam sinais novos para criar slots.")

    status = "ready" if proposed else "partial" if existing_count else "blocked"
    summary = (
        f"Plano autonomo de {horizon_days} dias: {len(proposed)} novo(s) slot(s), "
        f"{existing_count} item(ns) existente(s), {len(snapshots)} canal(is)."
    )

    return AutonomousCalendarPlan(
        project_id=project_id,
        horizon_days=horizon_days,
        mode=mode,
        status=status,
        summary=summary,
        existing_items=existing_count,
        proposed_items=proposed,
        gaps=gaps,
        risks=risks,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
