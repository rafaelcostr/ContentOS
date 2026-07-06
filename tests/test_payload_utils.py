"""Tests for LLM payload normalization."""

from contentos_shared.payload_utils import coerce_dict, normalize_research_output


def test_coerce_dict_from_string():
    assert coerce_dict("GTA 6") == {"title": "GTA 6"}


def test_coerce_dict_keeps_dict():
    data = {"title": "Test", "hook": "wow"}
    assert coerce_dict(data) == data


def test_normalize_research_selected_topic_string():
    data = normalize_research_output({"topics": [], "selected_topic": "GTA 6 leaks"})
    assert isinstance(data["selected_topic"], dict)
    assert data["selected_topic"]["title"] == "GTA 6 leaks"


def test_normalize_research_topics_strings():
    data = normalize_research_output({"topics": ["A", "B"], "selected_topic": {"title": "A"}})
    assert data["topics"][0]["title"] == "A"
    assert data["topics"][1]["title"] == "B"
