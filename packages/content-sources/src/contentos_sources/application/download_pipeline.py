"""HTTP download pipeline with size limits (V5.0)."""

from __future__ import annotations

import hashlib

import httpx
from contentos_sources.domain.media_license import max_download_bytes


class DownloadTooLargeError(ValueError):
    pass


class DownloadPipeline:
    """Fetch remote media bytes with timeout and size guard."""

    def __init__(self, timeout: float = 90.0) -> None:
        self.timeout = timeout

    async def download(self, url: str) -> tuple[bytes, str]:
        max_bytes = max_download_bytes()
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "video/mp4")
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise DownloadTooLargeError(
                            f"Download exceeds MEDIA_MAX_DOWNLOAD_MB ({max_bytes} bytes)"
                        )
                    chunks.append(chunk)
                return b"".join(chunks), content_type

    @staticmethod
    def sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()
