"""Prompt domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

PromptSuggestionStatus = Literal["pending", "approved", "rejected"]


@dataclass
class PromptVersion:
    version: str
    updated_at: datetime
    source: str  # bundled | override


@dataclass
class PromptSuggestion:
    id: str
    prompt_id: str
    proposed_version: str
    current_version: str
    score: float
    reason: str
    author: str
    content: str
    status: PromptSuggestionStatus = "pending"
    performance_basis: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    decided_at: str | None = None
    decided_by: str | None = None
    decision_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prompt_id": self.prompt_id,
            "proposed_version": self.proposed_version,
            "current_version": self.current_version,
            "score": self.score,
            "reason": self.reason,
            "author": self.author,
            "content": self.content,
            "status": self.status,
            "performance_basis": dict(self.performance_basis),
            "created_at": self.created_at,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
            "decision_reason": self.decision_reason,
        }


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
