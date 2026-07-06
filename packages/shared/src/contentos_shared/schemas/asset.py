from dataclasses import dataclass, field
from uuid import UUID, uuid4

from contentos_shared.enums import AssetCategory


@dataclass(frozen=True)
class AssetRef:
    id: UUID
    category: AssetCategory
    key: str
    bucket: str
    content_type: str
    size_bytes: int = 0


@dataclass
class AssetMeta:
    project_id: UUID | None = None
    pipeline_id: UUID | None = None
    job_id: UUID | None = None
    filename: str = ""
    content_type: str = "application/octet-stream"
    tags: dict[str, str] = field(default_factory=dict)

    def build_key(self, category: AssetCategory) -> str:
        ext = self.filename.rsplit(".", 1)[-1] if "." in self.filename else "bin"
        return f"{category.value}/{uuid4().hex[:12]}.{ext}"
