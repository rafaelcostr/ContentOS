"""Shared storage settings for agent handlers."""

import os

from contentos_storage.factory import StorageSettings


def agent_storage_settings() -> StorageSettings:
    return StorageSettings(
        endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "contentos"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "contentos_secret"),
        bucket=os.getenv("MINIO_BUCKET", "contentos"),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
    )
