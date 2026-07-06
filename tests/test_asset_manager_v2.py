"""Tests for Asset Manager V2 index service."""

import hashlib

from contentos_storage.application.asset_index_service import AssetIndexService


def test_compute_hash():
    data = b"hello contentos"
    h = AssetIndexService.compute_hash(data)
    assert h == hashlib.sha256(data).hexdigest()
    assert len(h) == 64
