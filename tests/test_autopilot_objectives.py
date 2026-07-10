from __future__ import annotations

from contentos_autopilot import build_objective_tree, objective_metadata_for_topic


def test_build_objective_tree_from_strategy_and_channels():
    tree = build_objective_tree(
        project_id="project-1",
        strategy={
            "positioning": "Virar referencia em GTA 6",
            "goals": ["Crescer Shorts", "Criar serie de curiosidades"],
            "cadence": {"weekly_posts": 3, "posting_hours": [18, 21]},
        },
        channels=[
            {
                "channel_id": "channel-1",
                "name": "Canal GTA",
                "platform": "youtube",
                "score": 82,
            }
        ],
    )
    data = tree.to_dict()

    levels = {node["level"] for node in data["nodes"]}

    assert {"project", "monthly", "weekly", "daily", "channel", "campaign"}.issubset(levels)
    assert any(node["metadata"].get("channel_id") == "channel-1" for node in data["nodes"])


def test_objective_metadata_links_topic_to_goal_path():
    tree = build_objective_tree(
        project_id="project-1",
        strategy={"positioning": "Autoridade em games", "goals": ["Criar serie de curiosidades"]},
    )

    metadata = objective_metadata_for_topic(
        tree=tree,
        topic="Criar serie de curiosidades sobre GTA 6",
    )

    assert metadata["objective_status"] == "linked"
    assert metadata["objective_id"]
    assert metadata["objective_path"]


def test_objective_metadata_falls_back_to_project_goal():
    tree = build_objective_tree(project_id="project-1", strategy={"positioning": "Educar gamers"})

    metadata = objective_metadata_for_topic(tree=tree, topic="Tema novo")

    assert metadata["objective_level"] == "project"
    assert metadata["objective_title"] == "Educar gamers"
