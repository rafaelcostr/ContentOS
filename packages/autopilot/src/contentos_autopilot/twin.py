"""Channel Digital Twin read model for Autopilot.

The twin composes existing Growth, memory, analytics, learning and community
signals into one strategic snapshot. It does not persist state or execute work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from contentos_autopilot.objectives import ObjectiveTree

TwinStatus = Literal["ready", "learning", "blocked"]


@dataclass(frozen=True)
class ChannelTwinSnapshot:
    channel_id: str
    project_id: str
    platform: str
    name: str
    status: TwinStatus
    confidence: str
    score: int
    summary: str
    identity: dict[str, Any] = field(default_factory=dict)
    brand_dna: dict[str, Any] = field(default_factory=dict)
    audience: dict[str, Any] = field(default_factory=dict)
    strategy: dict[str, Any] = field(default_factory=dict)
    objectives: dict[str, Any] = field(default_factory=dict)
    calendar: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, Any] = field(default_factory=dict)
    competitors: dict[str, Any] = field(default_factory=dict)
    community: dict[str, Any] = field(default_factory=dict)
    learning: dict[str, Any] = field(default_factory=dict)
    resources: dict[str, Any] = field(default_factory=dict)
    risks: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "platform": self.platform,
            "name": self.name,
            "status": self.status,
            "confidence": self.confidence,
            "score": self.score,
            "summary": self.summary,
            "identity": dict(self.identity),
            "brand_dna": dict(self.brand_dna),
            "audience": dict(self.audience),
            "strategy": dict(self.strategy),
            "objectives": dict(self.objectives),
            "calendar": dict(self.calendar),
            "performance": dict(self.performance),
            "competitors": dict(self.competitors),
            "community": dict(self.community),
            "learning": dict(self.learning),
            "resources": dict(self.resources),
            "risks": list(self.risks),
            "opportunities": list(self.opportunities),
            "next_actions": list(self.next_actions),
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _unique(items: list[Any], *, limit: int = 12) -> list[str]:
    out: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _calendar_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    planned = [item for item in items if item.get("status") == "planned"]
    scheduled = [item for item in items if item.get("status") in {"scheduled", "pending_schedule"}]
    next_item = next((item for item in [*scheduled, *planned] if item), None)
    return {
        "total": len(items),
        "planned": len(planned),
        "scheduled": len(scheduled),
        "next_item": next_item or {},
        "objective_links": [
            item.get("objective_id")
            for item in items
            if item.get("objective_id") or (item.get("metadata") or {}).get("objective_id")
        ],
    }


def _performance_summary(workspace: dict[str, Any], intelligence: dict[str, Any]) -> dict[str, Any]:
    rows = _as_list(workspace.get("performance"))
    historical = _as_dict(intelligence.get("historical_videos"))
    high = [row for row in rows if row.get("performance_tier") == "high"]
    low = [row for row in rows if row.get("performance_tier") == "low"]
    return {
        "total_media": historical.get("total_media", len(rows)),
        "high_performers": historical.get("high_performers", len(high)),
        "low_performers": historical.get("low_performers", len(low)),
        "winning_videos": historical.get("winning_videos") or [],
        "losing_videos": historical.get("losing_videos") or [],
        "winning_titles": historical.get("winning_titles") or [],
        "underperforming_titles": historical.get("underperforming_titles") or [],
        "latest_rows": rows[:10],
    }


def _community_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sentiments = [str(row.get("sentiment") or "").lower() for row in rows if row.get("sentiment")]
    questions = [row.get("question") or row.get("text") for row in rows if row.get("question") or row.get("text")]
    return {
        "comment_count": len(rows),
        "positive": sentiments.count("positive"),
        "negative": sentiments.count("negative"),
        "neutral": sentiments.count("neutral"),
        "recent_questions": _unique(questions, limit=8),
    }


def _twin_status(*, confidence: str, score: int, health: str, risks: list[str]) -> TwinStatus:
    risk_text = " ".join(risks).lower()
    if health == "critical" or "oauth" in risk_text or "sem credencial" in risk_text:
        return "blocked"
    if confidence == "low" or score < 45:
        return "learning"
    return "ready"


def build_channel_twin_snapshot(
    *,
    channel_intelligence: Mapping[str, Any] | Any,
    workspace: Mapping[str, Any] | Any | None = None,
    objectives: ObjectiveTree | None = None,
    closed_loop: Mapping[str, Any] | Any | None = None,
    community_rows: list[dict[str, Any]] | None = None,
    costs: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> ChannelTwinSnapshot:
    intelligence = _as_dict(channel_intelligence)
    workspace_data = _as_dict(workspace or {})
    loop = _as_dict(closed_loop or {})
    profile = _as_dict(workspace_data.get("profile") or {})
    scope = _as_dict(workspace_data.get("scope") or {})
    brand = _as_dict(intelligence.get("brand_identity"))
    visual = _as_dict(intelligence.get("visual_identity"))
    posting = _as_dict(intelligence.get("posting_intelligence"))
    competitors = _as_dict(intelligence.get("competitor_intelligence"))
    content_patterns = _as_dict(intelligence.get("content_patterns"))
    strategy = _as_dict(intelligence.get("strategy_context") or workspace_data.get("strategy") or {})
    calendar_items = [item for item in _as_list(workspace_data.get("calendar")) if isinstance(item, dict)]
    health = str(workspace_data.get("health_status") or "unknown")
    risks = _unique(
        [
            *list(intelligence.get("risks") or []),
            *list(loop.get("blockers") or []),
            f"Saude do canal: {health}" if health == "critical" else "",
        ],
        limit=12,
    )
    opportunities = _unique(
        [
            *list(intelligence.get("opportunities") or []),
            *[rec.get("title") for rec in _as_list(workspace_data.get("recommendations")) if isinstance(rec, dict)],
        ],
        limit=12,
    )
    next_cycle = _as_dict(loop.get("next_cycle"))
    next_actions = _unique(
        [
            *list(intelligence.get("next_questions") or []),
            *list(next_cycle.get("actions") or []),
            next_cycle.get("summary"),
        ],
        limit=12,
    )

    score = int(intelligence.get("score") or profile.get("score") or 0)
    confidence = str(intelligence.get("confidence") or "low")
    status = _twin_status(confidence=confidence, score=score, health=health, risks=risks)
    channel_id = str(intelligence.get("channel_id") or scope.get("channel_id") or profile.get("channel_id") or "")
    project_id = str(intelligence.get("project_id") or scope.get("project_id") or profile.get("project_id") or "")
    platform = str(intelligence.get("platform") or scope.get("platform") or profile.get("platform") or "")
    name = str(intelligence.get("name") or scope.get("channel_name") or profile.get("name") or "Canal")

    return ChannelTwinSnapshot(
        channel_id=channel_id,
        project_id=project_id,
        platform=platform,
        name=name,
        status=status,
        confidence=confidence,
        score=score,
        summary=str(intelligence.get("summary") or workspace_data.get("summary") or ""),
        identity={
            "niche": intelligence.get("niche") or "",
            "audience": intelligence.get("audience") or "",
            "profile": profile,
            "scope": scope,
        },
        brand_dna={
            "brand_identity": brand,
            "visual_identity": visual,
            "content_patterns": content_patterns,
        },
        audience={
            "description": intelligence.get("audience") or "",
            "posting_intelligence": posting,
            "community": _community_summary(community_rows or []),
        },
        strategy=strategy,
        objectives=objectives.to_dict() if objectives else {"project_id": project_id, "nodes": []},
        calendar=_calendar_summary(calendar_items),
        performance=_performance_summary(workspace_data, intelligence),
        competitors={
            "intelligence": competitors,
            "profiles": _as_list(workspace_data.get("competitors")),
        },
        community=_community_summary(community_rows or []),
        learning={
            "insights": _as_list(workspace_data.get("learning")),
            "closed_loop": loop,
        },
        resources={
            "assets": _as_list(workspace_data.get("assets")),
            "costs": dict(costs or {}),
            "health_status": health,
        },
        risks=risks,
        opportunities=opportunities,
        next_actions=next_actions,
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
    )
