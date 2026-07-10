"""HTTP download pipeline with size limits (V5.0)."""

from __future__ import annotations

import hashlib
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from contentos_sources.domain.media_license import max_download_bytes


class DownloadTooLargeError(ValueError):
    pass


class BlockedDownloadUrlError(ValueError):
    pass


_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
    }
)


def _is_blocked_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_download_url(url: str) -> None:
    """Reject URLs that target private networks or unsupported schemes (SSRF guard)."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise BlockedDownloadUrlError(f"Unsupported URL scheme: {parsed.scheme or '(none)'}")
    host = parsed.hostname
    if not host:
        raise BlockedDownloadUrlError("URL has no hostname")

    host_lower = host.lower().rstrip(".")
    if host_lower in _BLOCKED_HOSTNAMES or host_lower.endswith(".localhost"):
        raise BlockedDownloadUrlError(f"Blocked hostname: {host}")

    try:
        literal = ipaddress.ip_address(host_lower)
        if _is_blocked_ip(literal):
            raise BlockedDownloadUrlError(f"Blocked IP: {host}")
        return
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host_lower, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise BlockedDownloadUrlError(f"Could not resolve hostname: {host}") from exc

    if not infos:
        raise BlockedDownloadUrlError(f"Could not resolve hostname: {host}")

    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        resolved = ipaddress.ip_address(sockaddr[0])
        if _is_blocked_ip(resolved):
            raise BlockedDownloadUrlError(f"Hostname resolves to blocked IP: {sockaddr[0]}")


class DownloadPipeline:
    """Fetch remote media bytes with timeout and size guard."""

    def __init__(self, timeout: float = 90.0) -> None:
        self.timeout = timeout

    async def download(self, url: str) -> tuple[bytes, str]:
        validate_download_url(url)
        max_bytes = max_download_bytes()
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                redirect_host = response.url.host
                if redirect_host:
                    validate_download_url(str(response.url))
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
