"""Download pipeline SSRF guard tests."""

import pytest
from contentos_sources.application.download_pipeline import (
    BlockedDownloadUrlError,
    validate_download_url,
)


def test_validate_download_url_allows_https_public():
    validate_download_url("https://videos.pexels.com/video-files/123.mp4")


def test_validate_download_url_blocks_localhost():
    with pytest.raises(BlockedDownloadUrlError, match="Blocked"):
        validate_download_url("http://localhost/video.mp4")


def test_validate_download_url_blocks_private_ip():
    with pytest.raises(BlockedDownloadUrlError, match="blocked"):
        validate_download_url("http://192.168.1.1/video.mp4")


def test_validate_download_url_blocks_file_scheme():
    with pytest.raises(BlockedDownloadUrlError, match="scheme"):
        validate_download_url("file:///etc/passwd")
