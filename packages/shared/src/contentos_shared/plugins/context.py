"""Publication context passed to platform plugins."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class PublishContext:
    pipeline_id: UUID
    project_id: UUID
    topic: str
    script: dict[str, Any]
    base_metadata: dict[str, Any]
    render_ref: dict[str, Any] | None = None
    render_bytes: bytes | None = None
    render_public_url: str | None = None
    credentials: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class PlatformPublication:
    platform: str
    title: str
    description: str
    hashtags: list[str]
    status: str  # ready | dry_run | published | failed | skipped
    payload: dict[str, Any] = field(default_factory=dict)
    publish_url: str | None = None
    external_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "title": self.title,
            "description": self.description,
            "hashtags": self.hashtags,
            "status": self.status,
            "payload": self.payload,
            "publish_url": self.publish_url,
            "external_id": self.external_id,
            "error": self.error,
        }
