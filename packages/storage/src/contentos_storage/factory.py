from functools import lru_cache

from contentos_storage.domain.asset_manager import AssetManager
from contentos_storage.infrastructure.minio_manager import MinIOAssetManager


class StorageSettings:
    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "contentos",
        secret_key: str = "contentos_secret",
        bucket: str = "contentos",
        secure: bool = False,
    ) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.secure = secure


@lru_cache
def get_asset_manager(settings: StorageSettings | None = None) -> AssetManager:
    s = settings or StorageSettings()
    return MinIOAssetManager(
        endpoint=s.endpoint,
        access_key=s.access_key,
        secret_key=s.secret_key,
        bucket=s.bucket,
        secure=s.secure,
    )
