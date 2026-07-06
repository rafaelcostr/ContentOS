"""YouTube Shorts publish plugin."""

import httpx

from contentos_shared.plugins.context import PlatformPublication, PublishContext
from contentos_shared.plugins.publish_base import PublishPlugin
from contentos_shared.plugins.registry import PluginMeta


class YouTubeShortsPlugin(PublishPlugin):
    platform = "youtube"
    TITLE_MAX = 100

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="youtube",
            version="1.0.0",
            description="Publicação YouTube Shorts",
            hooks=["post_publish"],
        )

    async def prepare(self, context: PublishContext) -> PlatformPublication:
        base = context.base_metadata
        title = self._truncate(base.get("title", context.topic), self.TITLE_MAX)
        if "#shorts" not in title.lower():
            title = self._truncate(f"{title} #Shorts", self.TITLE_MAX)

        hashtags = self._normalize_hashtags(base.get("hashtags", []), 15)
        if not any(t.lower() == "#shorts" for t in hashtags):
            hashtags.insert(0, "#Shorts")

        description = base.get("description", "")
        if hashtags:
            description = f"{description}\n\n{' '.join(hashtags)}".strip()
        description = self._truncate(description, 5000)

        return PlatformPublication(
            platform=self.platform,
            title=title,
            description=description,
            hashtags=hashtags,
            status="ready",
            payload={
                "category_id": "22",
                "video_format": "1080x1920",
                "is_short": True,
                "render_key": (context.render_ref or {}).get("key"),
            },
        )

    async def _publish_live(
        self,
        context: PublishContext,
        prepared: PlatformPublication,
        credentials: dict,
    ) -> PlatformPublication:
        api_key = credentials.get("api_key")
        access_token = credentials.get("access_token")
        if not access_token:
            prepared.status = "failed"
            prepared.error = "Missing YouTube OAuth access_token"
            return prepared

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    "https://www.googleapis.com/upload/youtube/v3/videos",
                    params={
                        "part": "snippet,status",
                        "uploadType": "resumable",
                        "key": api_key or "",
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "snippet": {
                            "title": prepared.title,
                            "description": prepared.description,
                            "categoryId": prepared.payload.get("category_id", "22"),
                        },
                        "status": {"privacyStatus": credentials.get("privacy", "private")},
                    },
                )
                if resp.status_code >= 400:
                    prepared.status = "failed"
                    prepared.error = resp.text[:500]
                    return prepared
                prepared.status = "published"
                prepared.external_id = resp.headers.get("X-Goog-Upload-URL", "")[:64]
                prepared.publish_url = "https://studio.youtube.com/"
        except Exception as exc:
            prepared.status = "failed"
            prepared.error = str(exc)
        return prepared
