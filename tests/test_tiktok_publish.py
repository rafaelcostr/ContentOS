"""TikTok publish plugin — post-upload status polling."""

from uuid import uuid4

import pytest
from contentos_shared.plugins.context import PublishContext
from contentos_shared.plugins.platforms.tiktok import TikTokPlugin


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]):
        self._responses = list(responses)
        self.calls = 0

    async def post(self, url, **kwargs):
        self.calls += 1
        if not self._responses:
            return _FakeResponse(500, text="no responses")
        return self._responses.pop(0)

    async def put(self, url, **kwargs):
        return _FakeResponse(200)


@pytest.mark.asyncio
async def test_tiktok_poll_completes_on_publish_complete(monkeypatch):
    monkeypatch.setenv("TIKTOK_PUBLISH_POLL_INTERVAL_SEC", "0.01")
    monkeypatch.setenv("TIKTOK_PUBLISH_POLL_TIMEOUT_SEC", "1")

    plugin = TikTokPlugin()
    client = _FakeClient(
        [
            _FakeResponse(200, {"data": {"status": "PROCESSING_UPLOAD"}}),
            _FakeResponse(200, {"data": {"status": "PUBLISH_COMPLETE"}}),
        ]
    )
    status, data = await plugin._poll_publish_status(client, "token", "pub-123")
    assert status == "published"
    assert data["status"] == "PUBLISH_COMPLETE"
    assert client.calls == 2


@pytest.mark.asyncio
async def test_tiktok_poll_fails_on_api_error():
    plugin = TikTokPlugin()
    client = _FakeClient([_FakeResponse(403, text="forbidden")])
    status, data = await plugin._poll_publish_status(client, "token", "pub-123")
    assert status == "failed"
    assert "forbidden" in data["error"]


@pytest.mark.asyncio
async def test_tiktok_prepare_only_skips_live(monkeypatch):
    monkeypatch.setenv("PUBLISH_MODE", "prepare_only")
    plugin = TikTokPlugin()
    ctx = PublishContext(
        pipeline_id=uuid4(),
        project_id=uuid4(),
        topic="Test",
        script={},
        base_metadata={"title": "Hello"},
        render_ref={"key": "renders/x.mp4"},
        credentials={},
    )
    prepared = await plugin.prepare(ctx)
    result = await plugin.publish(ctx, prepared)
    assert result.status == "ready"
    assert result.payload.get("mode") == "prepare_only"
