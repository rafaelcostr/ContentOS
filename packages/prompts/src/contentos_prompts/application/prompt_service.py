"""Prompt Manager application service."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

from contentos_prompts.domain.prompt_version import PromptDefinition, PromptSuggestion, PromptVersion, RenderedPrompt
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
        self._suggestions_dir = self._override_dir / ".suggestions" if self._override_dir else None
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

    def update_prompt(self, prompt_id: str, content: str, *, author: str = "manual", reason: str = "manual_update") -> PromptDefinition:
        self._ensure_override_dirs()
        current = self._registry.get(prompt_id)
        if current:
            self._snapshot_prompt(prompt_id, current.raw_content, current.version, current.source)

        parsed = self._loader.parse_content(content, source="override", prompt_id=prompt_id)
        if parsed.id != prompt_id:
            raise ValueError(f"Frontmatter id '{parsed.id}' does not match '{prompt_id}'")

        target = self._override_dir / f"{prompt_id}.md"  # type: ignore[operator]
        target.write_text(content, encoding="utf-8")
        self._append_history(prompt_id, parsed.version, parsed.source, author=author, reason=reason)
        self._registry.register(parsed)
        return parsed

    def suggest_prompt_update(
        self,
        prompt_id: str,
        content: str,
        *,
        reason: str,
        author: str,
        score: float,
        performance_basis: dict[str, Any] | None = None,
    ) -> PromptSuggestion:
        self._ensure_override_dirs()
        current = self.get_prompt(prompt_id)
        parsed = self._loader.parse_content(content, source="suggestion", prompt_id=prompt_id)
        if parsed.id != prompt_id:
            raise ValueError(f"Frontmatter id '{parsed.id}' does not match '{prompt_id}'")
        if parsed.version == current.version:
            raise ValueError("Prompt suggestion must propose a new version")

        suggestion = PromptSuggestion(
            id=str(uuid.uuid4()),
            prompt_id=prompt_id,
            proposed_version=parsed.version,
            current_version=current.version,
            score=float(score),
            reason=reason,
            author=author,
            content=content,
            performance_basis=dict(performance_basis or {}),
            created_at=datetime.now(UTC).isoformat(),
        )
        self._write_suggestion(suggestion)
        return suggestion

    def list_suggestions(self, *, status: str | None = None) -> list[PromptSuggestion]:
        suggestions: list[PromptSuggestion] = []
        if not self._suggestions_dir or not self._suggestions_dir.is_dir():
            return suggestions
        for path in sorted(self._suggestions_dir.glob("*.json")):
            try:
                suggestion = self._suggestion_from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                continue
            if status and suggestion.status != status:
                continue
            suggestions.append(suggestion)
        return sorted(suggestions, key=lambda item: item.created_at, reverse=True)

    def get_suggestion(self, suggestion_id: str) -> PromptSuggestion:
        self._ensure_override_dirs()
        path = self._suggestions_dir / f"{suggestion_id}.json"  # type: ignore[operator]
        if not path.is_file():
            raise KeyError(f"Prompt suggestion not found: {suggestion_id}")
        return self._suggestion_from_dict(json.loads(path.read_text(encoding="utf-8")))

    def approve_suggestion(self, suggestion_id: str, *, approver: str, reason: str = "approved") -> PromptDefinition:
        suggestion = self.get_suggestion(suggestion_id)
        if suggestion.status != "pending":
            raise ValueError("Only pending suggestions can be approved")
        updated = self.update_prompt(
            suggestion.prompt_id,
            suggestion.content,
            author=approver,
            reason=f"approved_suggestion:{suggestion.id}:{reason}",
        )
        suggestion.status = "approved"
        suggestion.decided_at = datetime.now(UTC).isoformat()
        suggestion.decided_by = approver
        suggestion.decision_reason = reason
        self._write_suggestion(suggestion)
        return updated

    def reject_suggestion(self, suggestion_id: str, *, reviewer: str, reason: str = "rejected") -> PromptSuggestion:
        suggestion = self.get_suggestion(suggestion_id)
        if suggestion.status != "pending":
            raise ValueError("Only pending suggestions can be rejected")
        suggestion.status = "rejected"
        suggestion.decided_at = datetime.now(UTC).isoformat()
        suggestion.decided_by = reviewer
        suggestion.decision_reason = reason
        self._write_suggestion(suggestion)
        return suggestion

    def rollback_prompt(self, prompt_id: str, version: str, *, author: str, reason: str = "rollback") -> PromptDefinition:
        self._ensure_override_dirs()
        current = self.get_prompt(prompt_id)
        content = self._load_snapshot(prompt_id, version)
        if content is None and current.version == version:
            content = current.raw_content
        if not content:
            raise KeyError(f"Prompt version not found for rollback: {prompt_id}@{version}")
        return self.update_prompt(prompt_id, content, author=author, reason=f"rollback:{version}:{reason}")

    def render(self, prompt_id: str, variables: dict[str, str] | None = None) -> RenderedPrompt:
        prompt = self.get_prompt(prompt_id)
        vars_map = {k: "" for k in prompt.variables}
        if variables:
            vars_map.update({k: str(v) for k, v in variables.items()})
        system = self._loader.render_template(prompt.system_template, vars_map)
        user = self._loader.render_template(prompt.user_template, vars_map)
        return RenderedPrompt(id=prompt.id, version=prompt.version, system=system, user=user)

    def _ensure_override_dirs(self) -> None:
        if not self._override_dir:
            self._override_dir = Path(os.getenv("PROMPTS_OVERRIDE_DIR", "/data/prompts"))
        self._override_dir.mkdir(parents=True, exist_ok=True)
        if self._history_dir is None:
            self._history_dir = self._override_dir / ".history"
        if self._suggestions_dir is None:
            self._suggestions_dir = self._override_dir / ".suggestions"
        self._history_dir.mkdir(parents=True, exist_ok=True)
        self._suggestions_dir.mkdir(parents=True, exist_ok=True)

    def _append_history(self, prompt_id: str, version: str, source: str, *, author: str, reason: str) -> None:
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
                "author": author,
                "reason": reason,
                "content_file": f"{prompt_id}.{version}.md",
            },
        )
        history_file.write_text(json.dumps(entries[:50], indent=2), encoding="utf-8")

    def _snapshot_prompt(self, prompt_id: str, content: str, version: str, source: str) -> None:
        if not self._history_dir or not content:
            return
        snapshot = self._history_dir / f"{prompt_id}.{version}.md"
        if not snapshot.exists():
            snapshot.write_text(content, encoding="utf-8")
        history_file = self._history_dir / f"{prompt_id}.json"
        entries: list[dict] = []
        if history_file.is_file():
            try:
                entries = json.loads(history_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                entries = []
        if not any(str(item.get("version")) == version for item in entries):
            entries.append(
                {
                    "version": version,
                    "updated_at": datetime.now(UTC).isoformat(),
                    "source": source,
                    "author": "system",
                    "reason": "snapshot_before_update",
                    "content_file": snapshot.name,
                }
            )
            history_file.write_text(json.dumps(entries[:50], indent=2), encoding="utf-8")

    def _load_snapshot(self, prompt_id: str, version: str) -> str | None:
        if not self._history_dir:
            return None
        snapshot = self._history_dir / f"{prompt_id}.{version}.md"
        if snapshot.is_file():
            return snapshot.read_text(encoding="utf-8")
        return None

    def _write_suggestion(self, suggestion: PromptSuggestion) -> None:
        if not self._suggestions_dir:
            return
        path = self._suggestions_dir / f"{suggestion.id}.json"
        path.write_text(json.dumps(suggestion.to_dict(), indent=2), encoding="utf-8")

    def _suggestion_from_dict(self, data: dict[str, Any]) -> PromptSuggestion:
        return PromptSuggestion(
            id=str(data["id"]),
            prompt_id=str(data["prompt_id"]),
            proposed_version=str(data["proposed_version"]),
            current_version=str(data["current_version"]),
            score=float(data.get("score") or 0),
            reason=str(data.get("reason") or ""),
            author=str(data.get("author") or ""),
            content=str(data.get("content") or ""),
            status=str(data.get("status") or "pending"),  # type: ignore[arg-type]
            performance_basis=dict(data.get("performance_basis") or {}),
            created_at=str(data.get("created_at") or ""),
            decided_at=data.get("decided_at"),
            decided_by=data.get("decided_by"),
            decision_reason=data.get("decision_reason"),
        )


@lru_cache(maxsize=1)
def get_prompt_service() -> PromptService:
    return PromptService()


def reset_prompt_service_cache() -> None:
    get_prompt_service.cache_clear()
