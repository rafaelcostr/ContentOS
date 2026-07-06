"""Tier D2 — workflow builder validation."""

import pytest
from contentos_shared.workflow_validation import (
    WorkflowValidationError,
    custom_workflow_name,
    validate_slug,
    validate_workflow_steps,
)


def test_validate_slug_ok():
    assert validate_slug("quality-lite") == "quality-lite"


def test_validate_slug_rejects_builtin():
    with pytest.raises(WorkflowValidationError):
        validate_slug("v1-default")


def test_validate_steps_ok():
    steps = validate_workflow_steps(["research", "script", "publisher"])
    assert steps == ["research", "script", "publisher"]


def test_validate_steps_unknown():
    with pytest.raises(WorkflowValidationError):
        validate_workflow_steps(["research", "unknown_step"])


def test_validate_steps_duplicate():
    with pytest.raises(WorkflowValidationError):
        validate_workflow_steps(["research", "research"])


def test_custom_workflow_name():
    org = "11111111-1111-1111-1111-111111111111"
    assert custom_workflow_name(org, "lite") == f"org-{org}-lite"
