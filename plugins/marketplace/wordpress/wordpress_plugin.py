"""WordPress REST API publish plugin."""

import httpx
from contentos_shared.plugins.context import PlatformPublication, PublishContext
from contentos_shared.plugins.publish_base import PublishPlugin
from contentos_shared.plugins.registry import PluginMeta


class WordPressPlugin(PublishPlugin):
    platform = "wordpress"

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="wordpress",
            version="1.0.0",
            description="Cria post WordPress via REST API",
            hooks=["post_publish"],
        )

    async def prepare(self, context: PublishContext) -> PlatformPublication:
        base = context.base_metadata
        title = self._truncate(base.get("title", context.topic), 200)
        content = base.get("description", "")
        tags = [t.lstrip("#") for t in base.get("hashtags", [])]
        return PlatformPublication(
            platform=self.platform,
            title=title,
            description=content,
            hashtags=tags,
            status="ready",
            payload={"status": "draft", "tags": tags},
        )

    async def _publish_live(
        self,
        context: PublishContext,
        prepared: PlatformPublication,
        credentials: dict,
    ) -> PlatformPublication:
        site_url = (credentials.get("site_url") or "").rstrip("/")
        username = credentials.get("username")
        app_password = credentials.get("app_password")
        if not site_url or not username or not app_password:
            prepared.status = "failed"
            prepared.error = "Missing site_url, username, or app_password"
            return prepared
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{site_url}/wp-json/wp/v2/posts",
                    auth=(username, app_password),
                    json={
                        "title": prepared.title,
                        "content": prepared.description,
                        "status": prepared.payload.get("status", "draft"),
                    },
                )
                if resp.status_code >= 400:
                    prepared.status = "failed"
                    prepared.error = resp.text[:500]
                    return prepared
                data = resp.json()
                prepared.status = "published"
                prepared.external_id = str(data.get("id"))
                prepared.publish_url = data.get("link")
        except Exception as exc:
            prepared.status = "failed"
            prepared.error = str(exc)
        return prepared
