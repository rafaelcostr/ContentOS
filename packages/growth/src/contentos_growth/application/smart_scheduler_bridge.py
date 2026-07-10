"""Growth → Smart Scheduler bridge (Growth OS Fase 13)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from contentos_database.cron_helpers import compute_next_run, resolve_timezone

from contentos_growth.application.content_factory_bridge import build_growth_context_json
from contentos_growth.application.post_manager import is_text_content_type
from contentos_growth.domain import GrowthStrategy
from contentos_growth.platform_registry import default_content_type

SchedulingMode = Literal["manual", "assisted", "automatic"]


@dataclass(frozen=True)
class GrowthSchedulePlan:
    project_id: str
    calendar_item_id: str
    name: str
    topic: str
    cron_expression: str
    timezone: str
    workflow_name: str | None
    context_json: dict[str, Any]
    mode: SchedulingMode
    is_active: bool
    planned_for: str | None = None


def parse_planned_for(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def planned_for_to_cron(planned_for: datetime, tz_name: str = "UTC") -> str:
    tz = resolve_timezone(tz_name)
    local = planned_for.astimezone(tz) if planned_for.tzinfo else planned_for.replace(tzinfo=timezone.utc).astimezone(tz)
    return f"{local.minute} {local.hour} {local.day} {local.month} *"


def compute_schedule_next_run(cron_expression: str, tz_name: str) -> datetime:
    return compute_next_run(cron_expression, tz_name)


def normalize_scheduling_mode(mode: str | None) -> SchedulingMode:
    normalized = (mode or "assisted").strip().lower()
    if normalized in ("manual", "assisted", "automatic"):
        return normalized  # type: ignore[return-value]
    if normalized in ("auto", "automatico", "automático"):
        return "automatic"
    if normalized in ("assistido", "assist"):
        return "assisted"
    return "assisted"


def can_schedule_calendar_item(calendar_item: dict[str, Any]) -> tuple[bool, str | None]:
    metadata = dict(calendar_item.get("metadata") or {})
    content_type = str(metadata.get("content_type") or default_content_type(metadata.get("platform"))).lower()
    if is_text_content_type(content_type):
        return False, "Posts de texto não são agendados via pipeline. Use 'Gerar post' ou dispatch manual."
    if calendar_item.get("status") not in ("planned", "post_ready"):
        return False, f"Item não pode ser agendado no status {calendar_item.get('status')}"
    if metadata.get("schedule_id"):
        return False, "Item já possui agendamento Growth"
    planned = parse_planned_for(calendar_item.get("planned_for"))
    if not planned:
        return False, "Item sem data planejada (planned_for)"
    if planned <= datetime.now(timezone.utc):
        return False, "Data planejada já passou"
    return True, None


def build_growth_schedule_plan(
    *,
    calendar_item: dict[str, Any],
    strategy: GrowthStrategy | None = None,
    mode: SchedulingMode = "assisted",
    timezone: str = "UTC",
    workflow_name: str | None = None,
) -> GrowthSchedulePlan:
    ok, reason = can_schedule_calendar_item(calendar_item)
    if not ok:
        raise ValueError(reason or "Cannot schedule calendar item")

    if mode == "manual":
        raise ValueError("Modo manual não cria PipelineSchedule. Use produce/dispatch direto.")

    planned = parse_planned_for(calendar_item.get("planned_for"))
    assert planned is not None

    cron = planned_for_to_cron(planned, timezone)
    topic = str(calendar_item.get("topic") or calendar_item.get("title") or "Conteúdo Growth").strip()
    title = str(calendar_item.get("title") or topic)[:80]
    context = build_growth_context_json(calendar_item=calendar_item, strategy=strategy)
    context["growth_scheduling_mode"] = mode
    context["growth_scheduled_for"] = planned.isoformat()

    return GrowthSchedulePlan(
        project_id=str(calendar_item["project_id"]),
        calendar_item_id=str(calendar_item.get("id") or ""),
        name=f"Growth: {title}"[:120],
        topic=topic[:500],
        cron_expression=cron,
        timezone=timezone,
        workflow_name=workflow_name,
        context_json=context,
        mode=mode,
        is_active=mode == "automatic",
        planned_for=planned.isoformat(),
    )
