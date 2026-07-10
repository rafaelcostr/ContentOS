"""TikTok publish plugin."""

import asyncio
import os

import httpx

from contentos_shared.plugins.context import PlatformPublication, PublishContext
from contentos_shared.plugins.publish_base import PublishPlugin
from contentos_shared.plugins.registry import PluginMeta

_TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"


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

    @staticmethod
    def _poll_interval_sec() -> float:
        try:
            return max(1.0, float(os.getenv("TIKTOK_PUBLISH_POLL_INTERVAL_SEC", "3")))
        except ValueError:
            return 3.0

    @staticmethod
    def _poll_timeout_sec() -> float:
        try:
            return max(5.0, float(os.getenv("TIKTOK_PUBLISH_POLL_TIMEOUT_SEC", "120")))
        except ValueError:
            return 120.0

    async def _poll_publish_status(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        publish_id: str,
    ) -> tuple[str, dict]:
        """Poll TikTok until publish completes or fails."""
        deadline = asyncio.get_event_loop().time() + self._poll_timeout_sec()
        last_payload: dict = {}
        while asyncio.get_event_loop().time() < deadline:
            resp = await client.post(
                _TIKTOK_STATUS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                json={"publish_id": publish_id},
            )
            if resp.status_code >= 400:
                return "failed", {"error": resp.text[:500], "publish_id": publish_id}
            body = resp.json()
            data = body.get("data") or {}
            last_payload = data
            status = str(data.get("status") or "").upper()
            if status in {"PUBLISH_COMPLETE", "PUBLISHED"}:
                return "published", data
            if status in {"FAILED", "PUBLISH_FAILED"}:
                return "failed", data
            await asyncio.sleep(self._poll_interval_sec())
        return "processing", last_payload

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
        if not context.render_bytes:
            prepared.status = "failed"
            prepared.error = "Missing render bytes for TikTok upload"
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
                        "source_info": {
                            "source": "FILE_UPLOAD",
                            "video_size": len(context.render_bytes),
                            "chunk_size": len(context.render_bytes),
                            "total_chunk_count": 1,
                        },
                    },
                )
                if resp.status_code >= 400:
                    prepared.status = "failed"
                    prepared.error = resp.text[:500]
                    return prepared
                data = resp.json()
                upload_url = data.get("data", {}).get("upload_url")
                publish_id = data.get("data", {}).get("publish_id")
                if not upload_url:
                    prepared.status = "failed"
                    prepared.error = "TikTok upload_url missing from init response"
                    return prepared
                upload = await client.put(
                    upload_url,
                    content=context.render_bytes,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes 0-{len(context.render_bytes) - 1}/{len(context.render_bytes)}",
                    },
                )
                if upload.status_code >= 400:
                    prepared.status = "failed"
                    prepared.error = upload.text[:500]
                    return prepared

                prepared.external_id = publish_id
                prepared.payload["publish_id"] = publish_id

                if publish_id:
                    final_status, poll_data = await self._poll_publish_status(
                        client, access_token, publish_id
                    )
                    prepared.status = final_status
                    prepared.payload["tiktok_status"] = poll_data.get("status")
                    if final_status == "published":
                        prepared.publish_url = f"https://www.tiktok.com/@preview/{publish_id}"
                    elif final_status == "failed":
                        prepared.error = str(poll_data.get("fail_reason") or poll_data.get("error") or "TikTok publish failed")
                    else:
                        prepared.publish_url = f"https://www.tiktok.com/@preview/{publish_id}"
                        prepared.payload["poll_timeout"] = True
                else:
                    prepared.status = "published"
                    prepared.publish_url = "https://www.tiktok.com/"
        except Exception as exc:
            prepared.status = "failed"
            prepared.error = str(exc)
        return prepared
