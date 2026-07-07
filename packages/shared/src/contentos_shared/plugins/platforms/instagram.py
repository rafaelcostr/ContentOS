"""Instagram Reels publish plugin."""

import httpx

from contentos_shared.plugins.context import PlatformPublication, PublishContext
from contentos_shared.plugins.publish_base import PublishPlugin
from contentos_shared.plugins.registry import PluginMeta


class InstagramReelsPlugin(PublishPlugin):
    platform = "instagram"
    CAPTION_MAX = 2200
    HASHTAG_MAX = 30

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="instagram",
            version="1.0.0",
            description="Publicação Instagram Reels",
            hooks=["post_publish"],
        )

    async def prepare(self, context: PublishContext) -> PlatformPublication:
        base = context.base_metadata
        title = self._truncate(base.get("title", context.topic), 100)
        hashtags = self._normalize_hashtags(base.get("hashtags", []), self.HASHTAG_MAX)

        caption_parts = [base.get("description", title)]
        if hashtags:
            caption_parts.append(" ".join(hashtags))
        description = self._truncate("\n\n".join(p for p in caption_parts if p), self.CAPTION_MAX)

        return PlatformPublication(
            platform=self.platform,
            title=title,
            description=description,
            hashtags=hashtags,
            status="ready",
            payload={
                "media_type": "REELS",
                "video_format": "1080x1920",
                "share_to_feed": True,
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
        ig_user_id = credentials.get("instagram_user_id")
        if not access_token or not ig_user_id:
            prepared.status = "failed"
            prepared.error = "Missing Instagram access_token or instagram_user_id"
            return prepared
        video_url = (
            credentials.get("video_url")
            or prepared.payload.get("video_url")
            or context.render_public_url
        )
        if not video_url:
            prepared.status = "failed"
            prepared.error = "Missing public video_url for Instagram Reels publish"
            return prepared

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                container = await client.post(
                    f"https://graph.facebook.com/v19.0/{ig_user_id}/media",
                    params={
                        "access_token": access_token,
                        "media_type": "REELS",
                        "caption": prepared.description,
                        "video_url": video_url,
                    },
                )
                if container.status_code >= 400:
                    prepared.status = "failed"
                    prepared.error = container.text[:500]
                    return prepared
                creation_id = container.json().get("id")
                publish = await client.post(
                    f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish",
                    params={"access_token": access_token, "creation_id": creation_id},
                )
                if publish.status_code >= 400:
                    prepared.status = "failed"
                    prepared.error = publish.text[:500]
                    return prepared
                prepared.status = "published"
                prepared.external_id = publish.json().get("id")
                prepared.publish_url = f"https://www.instagram.com/reel/{prepared.external_id}/"
        except Exception as exc:
            prepared.status = "failed"
            prepared.error = str(exc)
        return prepared
