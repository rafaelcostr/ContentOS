import pytest
from contentos_shared.enums import AssetCategory


def test_asset_categories():
    assert AssetCategory.TAKES.value == "takes"
    assert AssetCategory.RENDERS.value == "renders"
    assert AssetCategory.CAPTIONS.value == "captions"
