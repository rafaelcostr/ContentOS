"""Tests for Prompt Manager."""

from pathlib import Path

import pytest
from contentos_prompts.application.prompt_service import PromptService
from contentos_prompts.infrastructure.loader import PromptLoader

SAMPLE_PROMPT = """---
id: test_agent
version: 1.0.0
agent: test_agent
variables:
  - topic
  - memory_context
system: |
  System for {{topic}}
user: |
  User message: {{topic}}
  Context: {{memory_context}}
---
"""


def test_loader_parses_frontmatter():
    loader = PromptLoader()
    prompt = loader.parse_content(SAMPLE_PROMPT, prompt_id="test_agent")
    assert prompt.id == "test_agent"
    assert prompt.version == "1.0.0"
    assert "topic" in prompt.variables
    assert "{{topic}}" in prompt.system_template


def test_loader_renders_variables():
    loader = PromptLoader()
    rendered = loader.render_template("Hello {{topic}} — {{memory_context}}", {"topic": "AI", "memory_context": "tech"})
    assert rendered == "Hello AI — tech"


def test_prompt_service_loads_bundled(tmp_path: Path):
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    (bundled / "research.md").write_text(SAMPLE_PROMPT.replace("test_agent", "research"), encoding="utf-8")
    service = PromptService(bundled_dir=bundled, override_dir=tmp_path / "override")
    prompts = service.list_prompts()
    assert len(prompts) == 1
    assert prompts[0]["id"] == "research"


def test_prompt_service_render(tmp_path: Path):
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    (bundled / "research.md").write_text(SAMPLE_PROMPT.replace("test_agent", "research"), encoding="utf-8")
    service = PromptService(bundled_dir=bundled)
    rendered = service.render("research", {"topic": "viral hooks", "memory_context": "fast pace"})
    assert "viral hooks" in rendered.system
    assert "viral hooks" in rendered.user
    assert rendered.version == "1.0.0"


def test_prompt_service_update_and_versions(tmp_path: Path):
    bundled = tmp_path / "bundled"
    override = tmp_path / "override"
    bundled.mkdir()
    (bundled / "research.md").write_text(SAMPLE_PROMPT.replace("test_agent", "research"), encoding="utf-8")
    service = PromptService(bundled_dir=bundled, override_dir=override)

    updated_content = SAMPLE_PROMPT.replace("test_agent", "research").replace("1.0.0", "1.1.0")
    updated = service.update_prompt("research", updated_content)
    assert updated.version == "1.1.0"
    assert updated.source == "override"

    versions = service.get_versions("research")
    assert len(versions) >= 1
    assert versions[0].version == "1.1.0"


def test_bundled_research_prompt_exists():
    root = Path(__file__).resolve().parents[1]
    prompts_dir = root / "packages" / "prompts" / "prompts"
    if not prompts_dir.is_dir():
        pytest.skip("bundled prompts dir not found")
    service = PromptService(bundled_dir=prompts_dir)
    prompt = service.get_prompt("research")
    assert prompt.agent == "research"
    rendered = service.render("research", {"topic": "test", "niche": "tech", "memory_context": ""})
    assert "test" in rendered.user
