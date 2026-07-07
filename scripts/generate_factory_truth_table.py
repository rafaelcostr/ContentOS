"""Regenerate docs/FACTORY_TRUTH_TABLE.md from code."""

from __future__ import annotations

from pathlib import Path

from contentos_shared.factory_truth import format_factory_truth_markdown

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "FACTORY_TRUTH_TABLE.md"


def main() -> None:
    OUT.write_text(format_factory_truth_markdown(), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
