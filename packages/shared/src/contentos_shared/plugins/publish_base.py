"""Base class for platform publish plugins."""

import os
from abc import abstractmethod

from contentos_shared.plugins.context import PlatformPublication, PublishContext
from contentos_shared.plugins.registry import ContentOSPlugin, PluginMeta


class PublishPlugin(ContentOSPlugin):
    """Prepare and optionally publish videos to a social platform."""

    platform: str = "base"

    @property
    @abstractmethod
    def meta(self) -> PluginMeta: ...

    async def on_load(self) -> None:
        pass

    async def on_unload(self) -> None:
        pass

    @abstractmethod
    async def prepare(self, context: PublishContext) -> PlatformPublication:
        """Format metadata for the platform."""

    async def publish(self, context: PublishContext, prepared: PlatformPublication) -> PlatformPublication:
        """Publish video — dry_run unless PUBLISH_MODE=live and credentials exist."""
        mode = os.getenv("PUBLISH_MODE", "dry_run").lower()
        creds = context.credentials.get(self.platform)

        if mode != "live" or not creds:
            prepared.status = "dry_run"
            prepared.publish_url = self._preview_url(context)
            prepared.payload["mode"] = "dry_run"
            return prepared

        return await self._publish_live(context, prepared, creds)

    @abstractmethod
    async def _publish_live(
        self,
        context: PublishContext,
        prepared: PlatformPublication,
        credentials: dict,
    ) -> PlatformPublication:
        """Platform-specific live upload."""

    def _preview_url(self, context: PublishContext) -> str:
        return f"https://contentos.local/preview/{self.platform}/{context.pipeline_id}"

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3].rstrip() + "..."

    @staticmethod
    def _normalize_hashtags(tags: list[str], max_count: int) -> list[str]:
        result: list[str] = []
        for tag in tags:
            clean = tag.strip().lstrip("#")
            if clean and clean not in result:
                result.append(f"#{clean}")
            if len(result) >= max_count:
                break
        return result
