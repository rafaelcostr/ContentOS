"""Discord webhook publish plugin."""

import httpx
from contentos_shared.plugins.context import PlatformPublication, PublishContext
from contentos_shared.plugins.publish_base import PublishPlugin
from contentos_shared.plugins.registry import PluginMeta


class DiscordPlugin(PublishPlugin):
    platform = "discord"

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="discord",
            version="1.0.0",
            description="Notifica canal Discord com metadados do vídeo",
            hooks=["post_publish"],
        )

    async def prepare(self, context: PublishContext) -> PlatformPublication:
        base = context.base_metadata
        title = base.get("title", context.topic)
        description = self._truncate(base.get("description", ""), 2000)
        return PlatformPublication(
            platform=self.platform,
            title=title,
            description=description,
            hashtags=self._normalize_hashtags(base.get("hashtags", []), 8),
            status="ready",
            payload={"embed_color": 5814783},
        )

    async def _publish_live(
        self,
        context: PublishContext,
        prepared: PlatformPublication,
        credentials: dict,
    ) -> PlatformPublication:
        webhook_url = credentials.get("webhook_url")
        if not webhook_url:
            prepared.status = "failed"
            prepared.error = "Missing webhook_url"
            return prepared
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    webhook_url,
                    json={
                        "embeds": [
                            {
                                "title": prepared.title,
                                "description": prepared.description,
                                "color": prepared.payload.get("embed_color", 5814783),
                            }
                        ]
                    },
                )
                if resp.status_code >= 400:
                    prepared.status = "failed"
                    prepared.error = resp.text[:500]
                    return prepared
                prepared.status = "published"
                prepared.publish_url = webhook_url.split("/api/webhooks")[0]
        except Exception as exc:
            prepared.status = "failed"
            prepared.error = str(exc)
        return prepared
