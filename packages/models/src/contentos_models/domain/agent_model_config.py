"""Per-agent model configuration."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AgentModelConfig:
    agent: str
    provider_type: str  # text | speech | subtitle | compute
    provider: str
    model: str
    updated_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "provider_type": self.provider_type,
            "provider": self.provider,
            "model": self.model,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
