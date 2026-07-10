"""Content Strategist — automatic content plan (Growth OS Fase 9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from contentos_growth.domain import ChannelProfile, ContentCalendar, GrowthRecommendation, GrowthStrategy
from contentos_growth.platform_registry import default_content_type, get_platform_profile, normalize_platform_id


@dataclass(frozen=True)
class ContentStrategyPlan:
    project_id: str
    strategy: GrowthStrategy
    calendar: ContentCalendar
    campaigns: list[dict[str, Any]] = field(default_factory=list)
    channel_goals: dict[str, list[str]] = field(default_factory=dict)
    summary: str = ""
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "strategy": self.strategy.to_dict(),
            "calendar": self.calendar.to_dict(),
            "campaigns": list(self.campaigns),
            "channel_goals": dict(self.channel_goals),
            "summary": self.summary,
            "generated_at": self.generated_at,
        }


def _collect_topics(
    recommendations: list[GrowthRecommendation],
    opportunities: list[str],
    channel_hooks: list[str],
) -> list[str]:
    topics: list[str] = []
    for rec in recommendations:
        title = (rec.title or "").strip()
        if title and title not in topics:
            topics.append(title[:200])
    for opp in opportunities:
        text = opp.strip()
        if text and text not in topics:
            topics.append(text[:200])
    for hook in channel_hooks:
        if hook and hook not in topics:
            topics.append(hook[:200])
    if not topics:
        topics = [
            "Conteúdo educativo no nicho",
            "Short com hook de curiosidade",
            "Vídeo com CTA de engajamento",
        ]
    return topics


def _infer_weekly_posts(channels: list[ChannelProfile], posting_gap_days: float | None) -> int:
    if posting_gap_days is not None:
        if posting_gap_days <= 3:
            return 4
        if posting_gap_days <= 7:
            return 3
        return 2
    return 3 if channels else 2


def _infer_posting_hours(channel_hours: list[int]) -> list[int]:
    if channel_hours:
        return sorted(set(channel_hours))[:4]
    return [12, 18, 20]


def _build_campaigns(
    *,
    positioning: str,
    channels: list[ChannelProfile],
    opportunities: list[str],
) -> list[dict[str, Any]]:
    campaigns: list[dict[str, Any]] = []
    if positioning:
        campaigns.append(
            {
                "name": "Campanha de posicionamento",
                "goal": positioning[:240],
                "duration_days": 30,
                "channels": [ch.channel_id for ch in channels[:3]],
            }
        )
    if opportunities:
        campaigns.append(
            {
                "name": "Oportunidades detectadas",
                "goal": opportunities[0][:240],
                "duration_days": 14,
                "channels": [ch.channel_id for ch in channels[:2]],
            }
        )
    for ch in channels:
        if ch.score and ch.score < 60:
            campaigns.append(
                {
                    "name": f"Boost {ch.name}",
                    "goal": f"Elevar Growth Score do canal (atual {ch.score:.0f})",
                    "duration_days": 21,
                    "channels": [ch.channel_id],
                }
            )
    return campaigns[:4]


def _build_channel_goals(channels: list[ChannelProfile]) -> dict[str, list[str]]:
    goals: dict[str, list[str]] = {}
    for ch in channels:
        items: list[str] = []
        profile = ch.profile or {}
        shorts_ratio = profile.get("shorts_ratio")
        if shorts_ratio is not None and float(shorts_ratio) < 0.3:
            items.append("Aumentar proporção de Shorts")
        if not ch.analyzed_at:
            items.append("Sincronizar e analisar canal")
        elif ch.score < 70:
            items.append(f"Melhorar score Growth para 70+ (atual {ch.score:.0f})")
        if not items:
            items.append("Manter cadência e testar novos hooks")
        goals[ch.channel_id] = items
    return goals


def _pick_content_type(platform: str, index: int) -> str:
    return default_content_type(platform, index)


def _weekly_posts_for_platform(platform: str, base: int) -> int:
    profile = get_platform_profile(platform)
    if profile:
        return max(base, profile.weekly_posts_default // 2) if base < 2 else min(profile.weekly_posts_default, base + 1)
    return base


def _build_calendar_items(
    *,
    project_id: str,
    channels: list[ChannelProfile],
    topics: list[str],
    weekly_posts: int,
    posting_hours: list[int],
    horizon_days: int,
    campaigns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not channels:
        channels = [
            ChannelProfile(
                channel_id="default",
                project_id=project_id,
                platform="youtube",
                name="Canal principal",
            )
        ]

    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    spacing = max(1, 7 // max(weekly_posts, 1))
    items: list[dict[str, Any]] = []
    topic_idx = 0
    campaign_idx = 0

    for day_offset in range(horizon_days):
        if day_offset % spacing != 0 and day_offset % 7 not in {1, 3, 5}:
            continue
        if len(items) >= weekly_posts * (horizon_days // 7 + 1):
            break

        channel = channels[len(items) % len(channels)]
        topic = topics[topic_idx % len(topics)]
        topic_idx += 1
        hour = posting_hours[len(items) % len(posting_hours)]
        planned = start + timedelta(days=day_offset, hours=hour)
        campaign = campaigns[campaign_idx % len(campaigns)]["name"] if campaigns else None
        if len(items) % 5 == 0 and campaigns:
            campaign_idx += 1

        items.append(
            {
                "channel_id": None if channel.channel_id == "default" else channel.channel_id,
                "title": topic[:120],
                "topic": topic,
                "planned_for": planned.isoformat(),
                "status": "planned",
                "metadata": {
                    "platform": normalize_platform_id(channel.platform),
                    "content_type": _pick_content_type(channel.platform, len(items)),
                    "campaign": campaign,
                    "source": "content_strategist",
                },
            }
        )

    return items


def generate_content_strategy_plan(
    *,
    project_id: str,
    channels: list[ChannelProfile],
    recommendations: list[GrowthRecommendation],
    positioning: str,
    opportunities: list[str] | None = None,
    channel_memory_by_channel: dict[str, dict[str, Any]] | None = None,
    posting_gap_days: float | None = None,
    horizon_days: int = 30,
    base_strategy: GrowthStrategy | None = None,
) -> ContentStrategyPlan:
    """Heuristic strategist — uses Growth signals, no parallel planning module."""
    opportunities = opportunities or []
    memory_by_channel = channel_memory_by_channel or {}

    all_hooks: list[str] = []
    all_hours: list[int] = []
    for data in memory_by_channel.values():
        all_hooks.extend(data.get("top_hooks") or [])
        all_hours.extend(data.get("best_posting_hours") or [])

    weekly_posts = _infer_weekly_posts(channels, posting_gap_days)
    posting_hours = _infer_posting_hours(all_hours)
    topics = _collect_topics(recommendations, opportunities, all_hooks)
    campaigns = _build_campaigns(positioning=positioning, channels=channels, opportunities=opportunities)
    channel_goals = _build_channel_goals(channels)

    goals = list(base_strategy.goals) if base_strategy and base_strategy.goals else []
    if positioning and positioning not in goals:
        goals.insert(0, positioning)
    for ch_id, ch_goals in channel_goals.items():
        ch_name = next((c.name for c in channels if c.channel_id == ch_id), ch_id[:8])
        goals.append(f"{ch_name}: {ch_goals[0]}")

    cadence = {
        "weekly_posts": weekly_posts,
        "monthly_posts": weekly_posts * 4,
        "posting_hours": posting_hours,
        "review_cycle": "weekly",
        "horizon_days": horizon_days,
        "campaigns": campaigns,
        "channel_goals": channel_goals,
    }

    kpis = dict(base_strategy.kpis) if base_strategy else {}
    kpis.update(
        {
            "positioning": positioning,
            "planned_items": len(topics),
            "active_channels": len(channels),
        }
    )

    strategy = GrowthStrategy(
        project_id=project_id,
        channel_id=base_strategy.channel_id if base_strategy else None,
        positioning=positioning,
        goals=goals[:12],
        kpis=kpis,
        cadence=cadence,
        id=base_strategy.id if base_strategy else None,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )

    calendar_items = _build_calendar_items(
        project_id=project_id,
        channels=channels,
        topics=topics,
        weekly_posts=weekly_posts,
        posting_hours=posting_hours,
        horizon_days=horizon_days,
        campaigns=campaigns,
    )

    summary = (
        f"Plano de {horizon_days} dias — {weekly_posts} postagens/semana, "
        f"{len(calendar_items)} slots, {len(campaigns)} campanha(s), "
        f"{len(channels)} canal(is)."
    )

    return ContentStrategyPlan(
        project_id=project_id,
        strategy=strategy,
        calendar=ContentCalendar(project_id=project_id, items=calendar_items, horizon_days=horizon_days),
        campaigns=campaigns,
        channel_goals=channel_goals,
        summary=summary,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
