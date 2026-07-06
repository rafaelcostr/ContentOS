"""Tier A2 — advanced asset search metadata."""

from contentos_storage.domain.asset_metadata import facet_tags, normalize_asset_metadata


def test_normalize_from_topic_and_scene():
    meta = normalize_asset_metadata(
        topic="GTA 6",
        scene={"label": "chase", "visual_hint": "car night", "tags": ["action"]},
        candidate={"source_id": "local_library", "candidate_id": "c1", "title": "Night drive"},
    )
    assert meta["theme"] == "GTA 6"
    assert meta["game"] == "GTA 6"
    assert meta["scene_label"] == "chase"
    assert meta["source_id"] == "local_library"
    assert any("car night" in o.lower() or "action" in o.lower() for o in meta["objects"])


def test_normalize_explicit_facets():
    meta = normalize_asset_metadata(
        topic="Fortnite",
        candidate={
            "metadata": {
                "character": "Jonesy",
                "motion": "pan-left",
                "color": "purple",
                "game": "Fortnite",
            }
        },
    )
    assert meta["character"] == "Jonesy"
    assert meta["motion"] == "pan-left"
    assert meta["color"] == "purple"
    assert meta["game"] == "Fortnite"


def test_facet_tags_include_prefixed_keys():
    meta = {
        "theme": "GTA 6",
        "game": "GTA 6",
        "character": "Lucia",
        "motion": "zoom-in",
        "objects": ["car", "city"],
    }
    tags = facet_tags(meta)
    assert "theme:GTA 6" in tags
    assert "character:Lucia" in tags
    assert "motion:zoom-in" in tags
    assert "object:car" in tags
    assert "GTA 6" in tags


def test_asset_search_filters_dataclass():
    from contentos_storage.application.asset_index_service import AssetSearchFilters

    filters = AssetSearchFilters(theme="GTA", game="GTA 6", motion="pan", limit=10)
    assert filters.theme == "GTA"
    assert filters.limit == 10
