"""Tier B8 — creative auto-retry decision (ADR-006)."""

from contentos_workflow.engine import should_creative_retry


def test_passed_advances():
    assert should_creative_retry(passed=True, retry_count=0, max_retries=1) == "advance"


def test_failed_retries_when_budget_left():
    assert should_creative_retry(passed=False, retry_count=0, max_retries=1) == "retry"
    assert should_creative_retry(passed=False, retry_count=1, max_retries=2) == "retry"


def test_failed_exhausts_budget():
    assert should_creative_retry(passed=False, retry_count=1, max_retries=1) == "advance_exhausted"
    assert should_creative_retry(passed=False, retry_count=2, max_retries=2) == "advance_exhausted"


def test_zero_max_retries_never_retries():
    assert should_creative_retry(passed=False, retry_count=0, max_retries=0) == "advance_exhausted"
