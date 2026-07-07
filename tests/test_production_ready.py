"""V5.5.5 — Production ready checklist and roadmap closure."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _read(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def test_production_ready_doc_exists():
    assert (DOCS / "PRODUCTION_READY.md").is_file()


def test_production_ready_covers_v5_enterprise():
    text = _read("PRODUCTION_READY.md")
    for section in (
        "KEDA",
        "SLO",
        "load test",
        "Command Center",
        "/health/ready",
        "GATEWAY_RATE_LIMIT",
        "Sign-off",
    ):
        assert section.lower() in text.lower(), section


def test_v5_roadmap_complete():
    text = _read("V5_ROADMAP.md")
    assert "**V5.5.5**" in text
    assert "**DONE**" in text
    assert "| **V5.5.5**" in text
    # No V5.5 item should remain TODO
    assert "V5.5.5" in text and "TODO" not in text.split("V5.5.5")[1].split("---")[0]


def test_v5_roadmap_all_phases_done():
    text = _read("V5_ROADMAP.md")
    for phase in ("V5.0.1", "V5.1.1", "V5.2.1", "V5.3.1", "V5.4.1", "V5.5.1"):
        chunk = text.split(phase, 1)[1].split("##", 1)[0]
        assert "**DONE**" in chunk, phase


def test_production_hardening_links_production_ready():
    text = _read("PRODUCTION_HARDENING.md")
    assert "PRODUCTION_READY.md" in text


def test_consolidation_map_v5_5_5():
    text = _read("V5_CONSOLIDATION_MAP.md")
    assert "V5.5.5" in text
    assert "**DONE**" in text
