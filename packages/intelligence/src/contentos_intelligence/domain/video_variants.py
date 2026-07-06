"""Video platform variants — Epic 2b."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VIDEO_PLATFORMS = frozenset({"tiktok", "youtube_shorts", "instagram_reels"})

UPCOMING_VIDEO_FORMATS = frozenset({"carousel", "podcast_script"})


@dataclass
class CropSpec:
    width: int = 1080
    height: int = 1920
    crop_bias: str = "center"
    max_duration_seconds: int = 60
    safe_zone: str = "vertical_full"

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "crop_bias": self.crop_bias,
            "max_duration_seconds": self.max_duration_seconds,
            "safe_zone": self.safe_zone,
        }


@dataclass
class VideoPlatformVariant:
    platform: str
    title: str
    description: str
    hashtags: list[str] = field(default_factory=list)
    crop_spec: CropSpec = field(default_factory=CropSpec)
    render_ref: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "title": self.title,
            "description": self.description,
            "hashtags": list(self.hashtags),
            "crop_spec": self.crop_spec.to_dict(),
            "render_ref": dict(self.render_ref) if self.render_ref else None,
            "metadata": dict(self.metadata),
            "source": self.source,
        }


@dataclass
class VideoVariantsReport:
    project_id: str
    pipeline_id: str | None
    topic: str
    variants: list[VideoPlatformVariant] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "pipeline_id": self.pipeline_id,
            "topic": self.topic,
            "variant_count": len(self.variants),
            "variants": [v.to_dict() for v in self.variants],
            "by_platform": {v.platform: v.to_dict() for v in self.variants},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VideoVariantsReport:
        variants: list[VideoPlatformVariant] = []
        for v in data.get("variants") or []:
            crop_data = v.get("crop_spec") or {}
            variants.append(
                VideoPlatformVariant(
                    platform=str(v.get("platform", "")),
                    title=str(v.get("title", "")),
                    description=str(v.get("description", "")),
                    hashtags=list(v.get("hashtags") or []),
                    crop_spec=CropSpec(
                        width=int(crop_data.get("width", 1080)),
                        height=int(crop_data.get("height", 1920)),
                        crop_bias=str(crop_data.get("crop_bias", "center")),
                        max_duration_seconds=int(crop_data.get("max_duration_seconds", 60)),
                        safe_zone=str(crop_data.get("safe_zone", "vertical_full")),
                    ),
                    render_ref=v.get("render_ref"),
                    metadata=dict(v.get("metadata") or {}),
                    source=str(v.get("source", "heuristic")),
                )
            )
        return cls(
            project_id=str(data.get("project_id", "")),
            pipeline_id=str(data["pipeline_id"]) if data.get("pipeline_id") else None,
            topic=str(data.get("topic", "")),
            variants=variants,
        )
