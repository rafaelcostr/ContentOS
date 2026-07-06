"""Load and parse .md prompt files with YAML frontmatter."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from contentos_prompts.domain.prompt_version import PromptDefinition


class PromptLoader:
    """Reads prompt definitions from .md files."""

    VARIABLE_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")

    def parse_file(self, path: Path, source: str = "bundled") -> PromptDefinition:
        raw = path.read_text(encoding="utf-8")
        return self.parse_content(raw, source=source, prompt_id=path.stem)

    def parse_content(self, raw: str, *, source: str = "bundled", prompt_id: str | None = None) -> PromptDefinition:
        meta, body = self._split_frontmatter(raw)
        prompt_id = str(meta.get("id") or prompt_id or "unknown")
        variables = meta.get("variables") or []
        if isinstance(variables, str):
            variables = [v.strip() for v in variables.split(",") if v.strip()]

        system = str(meta.get("system") or "").strip()
        user = str(meta.get("user") or "").strip()
        if not system and body:
            system, user = self._split_body_sections(body, user)

        return PromptDefinition(
            id=prompt_id,
            version=str(meta.get("version") or "1.0.0"),
            agent=str(meta.get("agent") or prompt_id),
            variables=list(variables),
            system_template=system,
            user_template=user,
            description=str(meta.get("description") or "").strip(),
            source=source,
            raw_content=raw,
        )

    def render_template(self, template: str, variables: dict[str, str]) -> str:
        def replacer(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(variables.get(key, ""))

        return self.VARIABLE_PATTERN.sub(replacer, template)

    def _split_frontmatter(self, raw: str) -> tuple[dict, str]:
        if not raw.startswith("---"):
            return {}, raw.strip()

        closed = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", raw, re.DOTALL)
        if closed:
            meta = yaml.safe_load(closed.group(1)) or {}
            body = closed.group(2).strip()
        else:
            open_fm = re.match(r"^---\r?\n(.*)$", raw, re.DOTALL)
            if not open_fm:
                return {}, raw.strip()
            meta = yaml.safe_load(open_fm.group(1)) or {}
            body = ""

        if not isinstance(meta, dict):
            meta = {}
        return meta, body

    def _split_body_sections(self, body: str, existing_user: str) -> tuple[str, str]:
        if "<!-- system -->" in body and "<!-- user -->" in body:
            _, system_part = body.split("<!-- system -->", 1)
            system_part, user_part = system_part.split("<!-- user -->", 1)
            return system_part.strip(), user_part.strip()
        if existing_user:
            return body.strip(), existing_user
        return body.strip(), ""
