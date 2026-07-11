"""Tests for Prompt Evolution approval and rollback."""

from pathlib import Path

from contentos_prompts.application.prompt_service import PromptService

SAMPLE_PROMPT = """---
id: research
version: 1.0.0
agent: research
variables:
  - topic
system: |
  System v1 for {{topic}}
user: |
  User v1: {{topic}}
---
"""

SUGGESTED_PROMPT = """---
id: research
version: 1.1.0
agent: research
variables:
  - topic
system: |
  System v2 for {{topic}}
user: |
  User v2: {{topic}}
---
"""


def _service(tmp_path: Path) -> PromptService:
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    (bundled / "research.md").write_text(SAMPLE_PROMPT, encoding="utf-8")
    return PromptService(bundled_dir=bundled, override_dir=tmp_path / "override")


def test_prompt_suggestion_does_not_overwrite_prompt(tmp_path: Path) -> None:
    service = _service(tmp_path)

    suggestion = service.suggest_prompt_update(
        "research",
        SUGGESTED_PROMPT,
        reason="Melhorar retenção em vídeos com baixa performance",
        author="autopilot",
        score=82,
        performance_basis={"retention_delta": 12},
    )

    current = service.get_prompt("research")

    assert suggestion.status == "pending"
    assert suggestion.proposed_version == "1.1.0"
    assert current.version == "1.0.0"
    assert service.list_suggestions(status="pending")[0].id == suggestion.id


def test_prompt_suggestion_requires_approval_to_apply(tmp_path: Path) -> None:
    service = _service(tmp_path)
    suggestion = service.suggest_prompt_update(
        "research",
        SUGGESTED_PROMPT,
        reason="CTR acima da média em variação testada",
        author="autopilot",
        score=91,
    )

    updated = service.approve_suggestion(suggestion.id, approver="editor", reason="approved by human")
    decided = service.get_suggestion(suggestion.id)
    versions = service.get_versions("research")

    assert updated.version == "1.1.0"
    assert decided.status == "approved"
    assert decided.decided_by == "editor"
    assert versions[0].version == "1.1.0"


def test_prompt_rollback_restores_previous_snapshot(tmp_path: Path) -> None:
    service = _service(tmp_path)
    suggestion = service.suggest_prompt_update(
        "research",
        SUGGESTED_PROMPT,
        reason="Teste de variação",
        author="autopilot",
        score=80,
    )
    service.approve_suggestion(suggestion.id, approver="editor")

    rolled_back = service.rollback_prompt("research", "1.0.0", author="editor", reason="performance dropped")

    assert rolled_back.version == "1.0.0"
    assert "System v1" in rolled_back.system_template
    assert service.render("research", {"topic": "GTA"}).version == "1.0.0"


def test_prompt_suggestion_can_be_rejected(tmp_path: Path) -> None:
    service = _service(tmp_path)
    suggestion = service.suggest_prompt_update(
        "research",
        SUGGESTED_PROMPT,
        reason="Mudança experimental",
        author="autopilot",
        score=55,
    )

    rejected = service.reject_suggestion(suggestion.id, reviewer="editor", reason="weak evidence")

    assert rejected.status == "rejected"
    assert service.get_prompt("research").version == "1.0.0"
