"""YouTube Shorts publish plugin."""

import httpx

from contentos_shared.plugins.context import PlatformPublication, PublishContext
from contentos_shared.plugins.publish_base import PublishPlugin
from contentos_shared.plugins.registry import PluginMeta

CHUNK_SIZE_BYTES = 5 * 1024 * 1024


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
        if not context.render_bytes:
            prepared.status = "failed"
            prepared.error = "Missing render bytes for YouTube upload"
            return prepared

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                init = await client.post(
                    "https://www.googleapis.com/upload/youtube/v3/videos",
                    params={
                        "part": "snippet,status",
                        "uploadType": "resumable",
                        "key": api_key or "",
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "X-Upload-Content-Type": "video/mp4",
                        "X-Upload-Content-Length": str(len(context.render_bytes)),
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
                if init.status_code >= 400:
                    prepared.status = "failed"
                    prepared.error = init.text[:500]
                    return prepared
                upload_url = init.headers.get("Location") or init.headers.get("X-Goog-Upload-URL")
                if not upload_url:
                    prepared.status = "failed"
                    prepared.error = "YouTube resumable upload URL missing"
                    return prepared

                data = await self._upload_resumable(client, upload_url, context.render_bytes, access_token)
                video_id = data.get("id")
                prepared.status = "published"
                prepared.external_id = video_id
                prepared.publish_url = (
                    f"https://www.youtube.com/watch?v={video_id}" if video_id else "https://studio.youtube.com/"
                )
                prepared.payload["upload_chunks"] = max(1, (len(context.render_bytes) + CHUNK_SIZE_BYTES - 1) // CHUNK_SIZE_BYTES)
        except Exception as exc:
            prepared.status = "failed"
            prepared.error = str(exc)
        return prepared

    async def _upload_resumable(
        self,
        client: httpx.AsyncClient,
        upload_url: str,
        data: bytes,
        access_token: str,
    ) -> dict:
        total = len(data)
        if total <= CHUNK_SIZE_BYTES:
            upload = await client.put(
                upload_url,
                content=data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(total),
                },
            )
            if upload.status_code >= 400:
                raise RuntimeError(upload.text[:500])
            return upload.json() if upload.content else {}

        offset = 0
        response: httpx.Response | None = None
        while offset < total:
            chunk = data[offset : offset + CHUNK_SIZE_BYTES]
            end = offset + len(chunk) - 1
            response = await client.put(
                upload_url,
                content=chunk,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{end}/{total}",
                },
            )
            if response.status_code == 308:
                range_header = response.headers.get("Range", "")
                if range_header.startswith("bytes=0-"):
                    offset = int(range_header.split("-")[1]) + 1
                else:
                    offset = end + 1
                continue
            if response.status_code >= 400:
                raise RuntimeError(response.text[:500])
            break
        if response is None:
            return {}
        return response.json() if response.content else {}
