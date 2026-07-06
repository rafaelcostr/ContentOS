"""TikTok publish plugin."""

import httpx

from contentos_shared.plugins.context import PlatformPublication, PublishContext
from contentos_shared.plugins.publish_base import PublishPlugin
from contentos_shared.plugins.registry import PluginMeta


class TikTokPlugin(PublishPlugin):
    platform = "tiktok"
    TITLE_MAX = 150
    HASHTAG_MAX = 5

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="tiktok",
            version="1.0.0",
            description="Publicação TikTok — vídeos verticais até 60s",
            hooks=["post_publish"],
        )

    async def prepare(self, context: PublishContext) -> PlatformPublication:
        base = context.base_metadata
        title = self._truncate(base.get("title", context.topic), self.TITLE_MAX)
        hashtags = self._normalize_hashtags(base.get("hashtags", []), self.HASHTAG_MAX)
        desc_parts = [base.get("description", "")]
        if hashtags:
            desc_parts.append(" ".join(hashtags))
        description = self._truncate("\n\n".join(p for p in desc_parts if p), 2200)

        return PlatformPublication(
            platform=self.platform,
            title=title,
            description=description,
            hashtags=hashtags,
            status="ready",
            payload={
                "video_format": "1080x1920",
                "max_duration_seconds": 60,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "render_key": (context.render_ref or {}).get("key"),
            },
        )

    async def _publish_live(
        self,
        context: PublishContext,
        prepared: PlatformPublication,
        credentials: dict,
    ) -> PlatformPublication:
        access_token = credentials.get("access_token")
        if not access_token:
            prepared.status = "failed"
            prepared.error = "Missing TikTok access_token in channel credentials"
            return prepared

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    "https://open.tiktokapis.com/v2/post/publish/video/init/",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "post_info": {
                            "title": prepared.title,
                            "description": prepared.description,
                            "privacy_level": prepared.payload.get("privacy_level"),
                        },
                        "source_info": {"source": "FILE_UPLOAD"},
                    },
                )
                if resp.status_code >= 400:
                    prepared.status = "failed"
                    prepared.error = resp.text[:500]
                    return prepared
                data = resp.json()
                prepared.status = "published"
                prepared.external_id = data.get("data", {}).get("publish_id")
                prepared.publish_url = f"https://www.tiktok.com/@preview/{prepared.external_id}"
        except Exception as exc:
            prepared.status = "failed"
            prepared.error = str(exc)
        return prepared
