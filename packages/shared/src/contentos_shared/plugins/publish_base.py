"""Base class for platform publish plugins."""

from abc import abstractmethod

from contentos_shared.audiovisual_qa import normalize_publish_mode
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
        """Publish video according to PUBLISH_MODE.

        Modes:
        - dry_run: never calls external APIs.
        - prepare_only / prepare: returns formatted metadata without publishing.
        - live: requires platform credentials and lets the plugin complete the upload.
        """
        mode = normalize_publish_mode()
        creds = context.credentials.get(self.platform)

        if mode in {"prepare", "prepare_only"}:
            prepared.status = "ready"
            prepared.payload["mode"] = "prepare_only"
            return prepared

        if mode != "live":
            prepared.status = "dry_run"
            prepared.publish_url = self._preview_url(context)
            prepared.payload["mode"] = "dry_run"
            return prepared

        if not creds:
            prepared.status = "failed"
            prepared.error = f"Missing {self.platform} credentials for live publish"
            prepared.payload["mode"] = "live"
            return prepared

        prepared.payload["mode"] = "live"
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
