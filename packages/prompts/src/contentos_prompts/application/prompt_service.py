"""Prompt Manager application service."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from functools import lru_cache
from importlib import resources
from pathlib import Path

from contentos_prompts.domain.prompt_version import PromptDefinition, PromptVersion, RenderedPrompt
from contentos_prompts.infrastructure.loader import PromptLoader
from contentos_prompts.infrastructure.registry import PromptRegistry


def _bundled_prompts_dir() -> Path:
    env = os.getenv("PROMPTS_DIR")
    if env:
        return Path(env)
    try:
        root = resources.files("contentos_prompts").joinpath("../../prompts")
        return Path(str(root.resolve()))
    except Exception:
        return Path(__file__).resolve().parents[3] / "prompts"


class PromptService:
    """Loads, versions, and renders agent prompts."""

    def __init__(
        self,
        bundled_dir: Path | None = None,
        override_dir: Path | None = None,
    ) -> None:
        self._bundled_dir = bundled_dir or _bundled_prompts_dir()
        override = override_dir or os.getenv("PROMPTS_OVERRIDE_DIR")
        self._override_dir = Path(override) if override else None
        self._history_dir = self._override_dir / ".history" if self._override_dir else None
        self._loader = PromptLoader()
        self._registry = PromptRegistry()
        self.reload()

    def reload(self) -> None:
        self._registry.clear()
        if self._bundled_dir.is_dir():
            for path in sorted(self._bundled_dir.glob("*.md")):
                self._registry.register(self._loader.parse_file(path, source="bundled"))
        if self._override_dir and self._override_dir.is_dir():
            for path in sorted(self._override_dir.glob("*.md")):
                self._registry.register(self._loader.parse_file(path, source="override"))

    def list_prompts(self) -> list[dict]:
        return [p.to_dict() for p in self._registry.list_all()]

    def get_prompt(self, prompt_id: str) -> PromptDefinition:
        prompt = self._registry.get(prompt_id)
        if not prompt:
            raise KeyError(f"Prompt not found: {prompt_id}")
        return prompt

    def get_versions(self, prompt_id: str) -> list[PromptVersion]:
        prompt = self.get_prompt(prompt_id)
        versions = [PromptVersion(version=prompt.version, updated_at=datetime.now(UTC), source=prompt.source)]
        if self._history_dir:
            history_file = self._history_dir / f"{prompt_id}.json"
            if history_file.is_file():
                try:
                    stored = json.loads(history_file.read_text(encoding="utf-8"))
                    return [
                        PromptVersion(
                            version=str(item["version"]),
                            updated_at=datetime.fromisoformat(item["updated_at"]),
                            source=str(item.get("source", "override")),
                        )
                        for item in stored
                    ]
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass
        return versions

    def update_prompt(self, prompt_id: str, content: str) -> PromptDefinition:
        if not self._override_dir:
            self._override_dir = Path(os.getenv("PROMPTS_OVERRIDE_DIR", "/data/prompts"))
        self._override_dir.mkdir(parents=True, exist_ok=True)
        if self._history_dir is None:
            self._history_dir = self._override_dir / ".history"
        self._history_dir.mkdir(parents=True, exist_ok=True)

        parsed = self._loader.parse_content(content, source="override", prompt_id=prompt_id)
        if parsed.id != prompt_id:
            raise ValueError(f"Frontmatter id '{parsed.id}' does not match '{prompt_id}'")

        target = self._override_dir / f"{prompt_id}.md"
        target.write_text(content, encoding="utf-8")
        self._append_history(prompt_id, parsed.version, parsed.source)
        self._registry.register(parsed)
        return parsed

    def render(self, prompt_id: str, variables: dict[str, str] | None = None) -> RenderedPrompt:
        prompt = self.get_prompt(prompt_id)
        vars_map = {k: "" for k in prompt.variables}
        if variables:
            vars_map.update({k: str(v) for k, v in variables.items()})
        system = self._loader.render_template(prompt.system_template, vars_map)
        user = self._loader.render_template(prompt.user_template, vars_map)
        return RenderedPrompt(id=prompt.id, version=prompt.version, system=system, user=user)

    def _append_history(self, prompt_id: str, version: str, source: str) -> None:
        if not self._history_dir:
            return
        history_file = self._history_dir / f"{prompt_id}.json"
        entries: list[dict] = []
        if history_file.is_file():
            try:
                entries = json.loads(history_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                entries = []
        entries.insert(
            0,
            {
                "version": version,
                "updated_at": datetime.now(UTC).isoformat(),
                "source": source,
            },
        )
        history_file.write_text(json.dumps(entries[:20], indent=2), encoding="utf-8")


@lru_cache(maxsize=1)
def get_prompt_service() -> PromptService:
    return PromptService()


def reset_prompt_service_cache() -> None:
    get_prompt_service.cache_clear()
