"""Source query value object."""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class SourceQuery:
    scene_description: str
    visual_hint: str = ""
    duration_needed: float = 5.0
    tags: list[str] = field(default_factory=list)
    project_id: UUID | None = None
    scene_label: str = ""
    topic: str = ""
