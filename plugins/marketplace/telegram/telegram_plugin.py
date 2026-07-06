"""Telegram channel publish plugin."""

import httpx
from contentos_shared.plugins.context import PlatformPublication, PublishContext
from contentos_shared.plugins.publish_base import PublishPlugin
from contentos_shared.plugins.registry import PluginMeta


class TelegramPlugin(PublishPlugin):
    platform = "telegram"

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="telegram",
            version="1.0.0",
            description="Publica vídeo em canal Telegram",
            hooks=["post_publish"],
        )

    async def prepare(self, context: PublishContext) -> PlatformPublication:
        base = context.base_metadata
        caption = self._truncate(
            f"{base.get('title', context.topic)}\n\n{base.get('description', '')}",
            1024,
        )
        tags = self._normalize_hashtags(base.get("hashtags", []), 10)
        if tags:
            caption = f"{caption}\n\n{' '.join(tags)}"
        return PlatformPublication(
            platform=self.platform,
            title=base.get("title", context.topic),
            description=caption,
            hashtags=tags,
            status="ready",
            payload={"parse_mode": "HTML", "render_key": (context.render_ref or {}).get("key")},
        )

    async def _publish_live(
        self,
        context: PublishContext,
        prepared: PlatformPublication,
        credentials: dict,
    ) -> PlatformPublication:
        bot_token = credentials.get("bot_token")
        chat_id = credentials.get("chat_id")
        if not bot_token or not chat_id:
            prepared.status = "failed"
            prepared.error = "Missing bot_token or chat_id"
            return prepared
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": prepared.description[:4096]},
                )
                if resp.status_code >= 400:
                    prepared.status = "failed"
                    prepared.error = resp.text[:500]
                    return prepared
                data = resp.json()
                prepared.status = "published"
                prepared.external_id = str(data.get("result", {}).get("message_id"))
                prepared.publish_url = f"https://t.me/c/{chat_id}/{prepared.external_id}"
        except Exception as exc:
            prepared.status = "failed"
            prepared.error = str(exc)
        return prepared
