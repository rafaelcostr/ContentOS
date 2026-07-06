"""Tests for Content Relation Graph (V4.3.1 / Epic 11)."""

from __future__ import annotations

from types import SimpleNamespace

from contentos_events.domain.event_types import ALL_TYPES, GRAPH_UPDATED, resolve_event_type
from contentos_intelligence.application.content_graph.builder import _prompts_from_jobs, _specialist_from_jobs
from contentos_intelligence.domain.content_graph import (
    NODE_TYPES,
    RELATION_TYPES,
    GraphEdge,
    GraphNode,
    GraphView,
    NeighborsView,
    node_key,
)


def test_node_key_format():
    assert node_key("video", "abc-123") == "video:abc-123"


def test_graph_view_to_dict():
    view = GraphView(
        project_id="proj-1",
        nodes=[GraphNode("pipeline", "p1", "Topic")],
        edges=[
            GraphEdge("pipeline", "p1", "script", "s1", "produces"),
        ],
    )
    d = view.to_dict()
    assert d["node_count"] == 1
    assert d["edge_count"] == 1
    assert d["edges"][0]["relation"] == "produces"


def test_neighbors_view():
    node = GraphNode("script", "s1", "Roteiro")
    edge = GraphEdge("pipeline", "p1", "script", "s1", "produces")
    view = NeighborsView(node=node, outgoing=[], incoming=[edge])
    assert view.to_dict()["incoming"][0]["source_type"] == "pipeline"


def test_specialist_from_jobs():
    jobs = [
        SimpleNamespace(
            output_data={
                "specialist_selection": {
                    "specialist_id": "gaming",
                    "specialist": {"name": "Gaming"},
                }
            }
        )
    ]
    assert _specialist_from_jobs(jobs) == ("gaming", "Gaming")


def test_prompts_from_jobs():
    jobs = [
        SimpleNamespace(output_data={"prompts_used": {"script": "v3", "hook": "v2"}}),
        SimpleNamespace(output_data={"specialist_prompt_pack": {"gaming_hook": "..."}}),
    ]
    prompts = _prompts_from_jobs(jobs)
    ids = {p[0] for p in prompts}
    assert "script" in ids
    assert "gaming_hook" in ids


def test_node_and_relation_types():
    assert "video" in NODE_TYPES
    assert "specialist" in NODE_TYPES
    assert "produces" in RELATION_TYPES
    assert "derived_from" in RELATION_TYPES


def test_graph_updated_event_registered():
    assert GRAPH_UPDATED in ALL_TYPES
    assert resolve_event_type("GraphUpdated") == GRAPH_UPDATED
