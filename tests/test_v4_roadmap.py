"""V4 roadmap documentation structure tests."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _read(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def test_v4_roadmap_exists_and_has_phases() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.0" in text
    assert "V4.1" in text
    assert "V4.2" in text
    assert "V4.3" in text
    assert "content_intelligence" in text
    assert "v4-intelligence" in text


def test_v4_consolidation_map_covers_all_epics() -> None:
    text = _read("V4_CONSOLIDATION_MAP.md")
    for epic in range(1, 13):
        assert f"Epic {epic}" in text, f"Epic {epic} missing from consolidation map"


def test_v4_consolidation_actions_defined() -> None:
    text = _read("V4_CONSOLIDATION_MAP.md")
    for action in ("EXTEND", "COMPOSE", "NEW", "UI ONLY"):
        assert action in text


def test_adr_008_registered() -> None:
    text = _read("ADR.md")
    assert "ADR-008" in text
    assert "contentos_intelligence" in text or "packages/intelligence" in text
    assert "content_intelligence" in text


def test_v4_implementation_order_sequential() -> None:
    text = _read("V4_ROADMAP.md")
    ids = re.findall(r"V4\.\d+\.\d+", text)
    assert "V4.0.1" in ids
    assert "V4.0.2" in ids
    assert "V4.3.2" in ids


def test_roadmap_links_v4_tier() -> None:
    text = _read("ROADMAP.md")
    assert "V4_ROADMAP.md" in text
    assert "Tier F" in text


def test_v4_roadmap_v401_done() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.0.1" in text
    assert "DONE" in text


def test_v4_roadmap_v411_done() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.1.1" in text
    assert "AB_TESTING.md" in text or "A/B Testing" in text


def test_v4_roadmap_v412_done() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.1.2" in text
    assert "CONTENT_SCORE.md" in text or "Content Score" in text


def test_v4_roadmap_v413_done() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.1.3" in text
    assert "SPECIALISTS.md" in text or "Specialists" in text


def test_v4_roadmap_v421_done() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.2.1" in text
    assert "MULTI_CONTENT.md" in text or "Multi Content" in text


def test_v4_roadmap_v422_done() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.2.2" in text
    assert "video_variants" in text or "multi_content_video" in text


def test_v4_roadmap_v423_done() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.2.3" in text
    assert "LEARNING_ENGINE.md" in text or "Learning Engine" in text


def test_v4_roadmap_v424_done() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.2.4" in text
    assert "TREND_FORECAST.md" in text or "Trend Forecast" in text


def test_v4_roadmap_v431_done() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.3.1" in text
    assert "CONTENT_GRAPH.md" in text or "Content Relation Graph" in text


def test_v4_roadmap_v432_done() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4.3.2" in text
    assert "EXECUTIVE_DASHBOARD.md" in text or "Executive Dashboard" in text


def test_v4_roadmap_complete() -> None:
    text = _read("V4_ROADMAP.md")
    assert "V4 concluído" in text or "completo" in text.lower()


def test_intelligence_package_documented() -> None:
    text = (DOCS / "INTELLIGENCE.md").read_text(encoding="utf-8")
    assert "contentos_intelligence" in text
    assert "IntelligenceRegistry" in text
    assert "ab_testing" in text
    assert "content_score" in text
    assert "specialists" in text
    assert "multi_content" in text
    assert "multi_content_video" in text
    assert "learning" in text
    assert "trend_forecast" in text
    assert "content_graph" in text
    assert "executive" in text
