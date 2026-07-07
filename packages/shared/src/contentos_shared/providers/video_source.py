"""Video source provider — Strategy pattern for swappable take libraries."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from contentos_storage.domain.asset_manager import AssetManager

from contentos_shared.enums import AssetCategory
from contentos_shared.media_production import render_allow_placeholder


@dataclass
class VideoClip:
    label: str
    asset_key: str
    bucket: str
    duration_seconds: float | None = None


class VideoSourceProvider(ABC):
    @abstractmethod
    async def get_clips_for_scenes(self, theme: str, scene_labels: list[str]) -> list[VideoClip]: ...


class MinIOTakeLibraryProvider(VideoSourceProvider):
    """V1: local take library stored in MinIO under takes/ prefix."""

    def __init__(self, asset_manager: AssetManager, theme: str) -> None:
        self.asset_manager = asset_manager
        self.theme = theme.lower()

    async def get_clips_for_scenes(self, theme: str, scene_labels: list[str]) -> list[VideoClip]:
        import os

        from minio import Minio

        client = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "contentos"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "contentos_secret"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        )
        bucket = os.getenv("MINIO_BUCKET", "contentos")
        prefix = f"{AssetCategory.TAKES.value}/"
        clips: list[VideoClip] = []
        objects = client.list_objects(bucket, prefix=prefix, recursive=True)
        for obj in objects:
            if theme.lower() in obj.object_name.lower() or not scene_labels:
                label = obj.object_name.split("/")[-1].rsplit(".", 1)[0]
                clips.append(VideoClip(label=label, asset_key=obj.object_name, bucket=bucket))
        if not clips and scene_labels and render_allow_placeholder():
            prefix = f"{AssetCategory.TAKES.value}/"
            for i, label in enumerate(scene_labels):
                clips.append(VideoClip(label=label, asset_key=f"{prefix}placeholder_{i}.mp4", bucket=bucket))
        return clips[: max(len(scene_labels), 1)] if clips else []
