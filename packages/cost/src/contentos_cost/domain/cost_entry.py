"""Cost entry domain model."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class CostRecord:
    project_id: UUID
    pipeline_id: UUID | None
    job_id: UUID | None
    agent: str
    provider: str
    model: str
    operation: str
    tokens_input: int
    tokens_output: int
    duration_ms: int
    estimated_cost_usd: float
    from_cache: bool = False

    def to_dict(self) -> dict:
        return {
            "project_id": str(self.project_id),
            "pipeline_id": str(self.pipeline_id) if self.pipeline_id else None,
            "job_id": str(self.job_id) if self.job_id else None,
            "agent": self.agent,
            "provider": self.provider,
            "model": self.model,
            "operation": self.operation,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "duration_ms": self.duration_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
            "from_cache": self.from_cache,
        }
