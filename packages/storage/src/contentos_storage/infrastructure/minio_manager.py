import io
from uuid import uuid4

from contentos_shared.enums import AssetCategory
from contentos_shared.schemas.asset import AssetMeta, AssetRef
from contentos_storage.domain.asset_manager import AssetManager
from minio import Minio
from minio.error import S3Error


class MinIOAssetManager(AssetManager):
    """MinIO implementation of AssetManager (Strategy pattern)."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    async def store(self, category: AssetCategory, data: bytes, meta: AssetMeta) -> AssetRef:
        key = meta.build_key(category)
        self.client.put_object(
            self.bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=meta.content_type,
        )
        return AssetRef(
            id=uuid4(),
            category=category,
            key=key,
            bucket=self.bucket,
            content_type=meta.content_type,
            size_bytes=len(data),
        )

    async def get(self, ref: AssetRef) -> bytes:
        response = self.client.get_object(ref.bucket, ref.key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def get_presigned_url(self, ref: AssetRef, expires: int = 3600) -> str:
        from datetime import timedelta

        return self.client.presigned_get_object(ref.bucket, ref.key, expires=timedelta(seconds=expires))

    async def delete(self, ref: AssetRef) -> None:
        self.client.remove_object(ref.bucket, ref.key)

    async def exists(self, ref: AssetRef) -> bool:
        try:
            self.client.stat_object(ref.bucket, ref.key)
            return True
        except S3Error:
            return False

    async def get_metadata(self, ref: AssetRef) -> dict:
        stat = self.client.stat_object(ref.bucket, ref.key)
        return {
            "size": stat.size,
            "content_type": stat.content_type,
            "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
        }
