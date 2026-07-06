"""Asset repository protocol — persistence behind MinIO storage."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from contentos_database.models import Asset


class AssetRepository(Protocol):
    async def find_by_hash(self, sha256: str) -> Asset | None: ...

    async def save(self, asset: Asset) -> Asset: ...

    def find_by_hash_sync(self, sha256: str) -> Asset | None: ...

    def save_sync(self, asset: Asset) -> Asset: ...

    def get_sync(self, asset_id: UUID) -> Asset | None: ...
