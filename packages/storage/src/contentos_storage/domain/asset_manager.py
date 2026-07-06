"""Asset Manager — single abstraction over object storage (MinIO)."""

from abc import ABC, abstractmethod

from contentos_shared.enums import AssetCategory
from contentos_shared.schemas.asset import AssetMeta, AssetRef


class AssetManager(ABC):
    """All agents MUST use this interface. Never access files directly."""

    @abstractmethod
    async def store(
        self,
        category: AssetCategory,
        data: bytes,
        meta: AssetMeta,
    ) -> AssetRef:
        """Store bytes and return immutable reference."""

    @abstractmethod
    async def get(self, ref: AssetRef) -> bytes:
        """Retrieve raw bytes by reference."""

    @abstractmethod
    async def get_presigned_url(self, ref: AssetRef, expires: int = 3600) -> str:
        """Generate temporary download URL."""

    @abstractmethod
    async def delete(self, ref: AssetRef) -> None:
        """Remove asset from storage."""

    @abstractmethod
    async def exists(self, ref: AssetRef) -> bool:
        """Check if asset exists and is readable."""

    @abstractmethod
    async def get_metadata(self, ref: AssetRef) -> dict:
        """Return object metadata (size, content-type, etc.)."""
