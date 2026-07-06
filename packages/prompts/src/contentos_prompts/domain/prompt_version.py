"""Prompt domain models."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PromptVersion:
    version: str
    updated_at: datetime
    source: str  # bundled | override


@dataclass
class PromptDefinition:
    id: str
    version: str
    agent: str
    variables: list[str] = field(default_factory=list)
    system_template: str = ""
    user_template: str = ""
    description: str = ""
    source: str = "bundled"
    raw_content: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "version": self.version,
            "agent": self.agent,
            "variables": self.variables,
            "system_template": self.system_template,
            "user_template": self.user_template,
            "description": self.description,
            "source": self.source,
        }


@dataclass
class RenderedPrompt:
    id: str
    version: str
    system: str
    user: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "version": self.version,
            "system": self.system,
            "user": self.user,
        }
