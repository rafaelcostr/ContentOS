"""Cron helpers for pipeline schedules (V3 Tier D1)."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter


class InvalidCronError(ValueError):
    pass


def validate_cron(expression: str) -> str:
    expr = expression.strip()
    if not croniter.is_valid(expr):
        raise InvalidCronError(f"Invalid cron expression: {expr}")
    return expr


def resolve_timezone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name.strip() or "UTC")
    except ZoneInfoNotFoundError as exc:
        raise InvalidCronError(f"Unknown timezone: {tz_name}") from exc


def compute_next_run(
    cron_expression: str,
    tz_name: str = "UTC",
    *,
    base: datetime | None = None,
) -> datetime:
    expr = validate_cron(cron_expression)
    tz = resolve_timezone(tz_name)
    if base is None:
        local_base = datetime.now(tz)
    else:
        local_base = base.astimezone(tz) if base.tzinfo else base.replace(tzinfo=timezone.utc).astimezone(tz)
    nxt = croniter(expr, local_base).get_next(datetime)
    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=tz)
    return nxt.astimezone(timezone.utc)


def render_topic_template(topic: str, *, when: datetime | None = None) -> str:
    now = when or datetime.now(timezone.utc)
    return (
        topic.replace("{datetime}", now.strftime("%Y-%m-%d %H:%M UTC"))
        .replace("{date}", now.strftime("%Y-%m-%d"))
    )
