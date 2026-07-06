"""Tier D1 — pipeline scheduler."""

import pytest
from contentos_database.cron_helpers import (
    InvalidCronError,
    compute_next_run,
    render_topic_template,
    validate_cron,
)
from contentos_database.scheduler_service import scheduler_enabled, scheduler_interval_seconds


def test_validate_cron_ok():
    assert validate_cron("0 9 * * *") == "0 9 * * *"


def test_validate_cron_invalid():
    with pytest.raises(InvalidCronError):
        validate_cron("not a cron")


def test_compute_next_run():
    nxt = compute_next_run("0 9 * * *", "UTC")
    assert nxt.tzinfo is not None


def test_render_topic_template():
    topic = render_topic_template("Daily report {date}")
    assert "Daily report" in topic
    assert "{date}" not in topic


def test_scheduler_enabled(monkeypatch):
    monkeypatch.delenv("SCHEDULER_ENABLED", raising=False)
    assert scheduler_enabled() is True
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    assert scheduler_enabled() is False


def test_scheduler_interval():
    assert scheduler_interval_seconds() >= 15
