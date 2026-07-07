"""Audiovisual QA gate — unified publish readiness contract (phase 5 + 6)."""

from __future__ import annotations

import os
import re
from typing import Any

from contentos_shared.media_production import is_production_env
from contentos_shared.payload_utils import coerce_dict

_SRT_TIME = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)


def publish_require_qa() -> bool:
    raw = os.getenv("PUBLISH_REQUIRE_QA")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return is_production_env()


def normalize_publish_mode(raw: str | None = None) -> str:
    mode = (raw or os.getenv("PUBLISH_MODE", "dry_run")).strip().lower()
    if mode in {"prepare", "prepare_only"}:
        return "prepare_only"
    if mode == "live":
        return "live"
    return "dry_run"


def publish_mode_allows_live(mode: str | None = None) -> bool:
    return normalize_publish_mode(mode) == "live"


def _srt_timestamp_to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt_cues(srt_text: str) -> list[tuple[float, float]]:
    cues: list[tuple[float, float]] = []
    for match in _SRT_TIME.finditer(srt_text):
        start = _srt_timestamp_to_seconds(match.group(1), match.group(2), match.group(3), match.group(4))
        end = _srt_timestamp_to_seconds(match.group(5), match.group(6), match.group(7), match.group(8))
        if end > start:
            cues.append((start, end))
    return cues


def check_subtitle_sync(
    segments: list[dict[str, Any]],
    srt_text: str,
    *,
    tolerance_sec: float = 2.0,
) -> tuple[bool, str]:
    """Compare JSON segment timings with exported SRT cues."""
    if not segments:
        return True, "no segments"
    cues = parse_srt_cues(srt_text)
    if not cues:
        return False, "could not parse SRT cues"

    seg_start = float(segments[0].get("start", 0))
    cue_start = cues[0][0]
    if abs(seg_start - cue_start) > tolerance_sec:
        return False, f"first cue drift {abs(seg_start - cue_start):.1f}s (>{tolerance_sec}s)"

    seg_end = float(segments[-1].get("end", seg_start))
    cue_end = cues[-1][1]
    if abs(seg_end - cue_end) > tolerance_sec:
        return False, f"last cue drift {abs(seg_end - cue_end):.1f}s (>{tolerance_sec}s)"

    sample_count = min(3, len(segments), len(cues))
    for index in range(sample_count):
        seg = segments[index]
        cue = cues[index]
        start = float(seg.get("start", 0))
        if abs(start - cue[0]) > tolerance_sec:
            return False, f"cue #{index + 1} drift {abs(start - cue[0]):.1f}s"
    return True, "subtitle sync ok"


def evaluate_publish_gate(payload: dict[str, Any]) -> dict[str, Any]:
    """Aggregate QA signals for publisher gating."""
    review = coerce_dict(payload.get("video_review"))
    retention_report = coerce_dict(payload.get("retention_report"))

    quality_passed = bool(payload.get("quality_passed", False))
    video_review_passed = bool(payload.get("video_review_passed", review.get("passed", True)))
    if "retention_passed" in payload:
        retention_passed = bool(payload.get("retention_passed"))
    elif retention_report:
        retention_passed = bool(retention_report.get("passed", True))
    else:
        retention_passed = True

    block_reasons: list[str] = []
    if not quality_passed:
        block_reasons.append("quality")
    if not video_review_passed:
        block_reasons.append("video_review")
    if not retention_passed:
        block_reasons.append("retention")

    publishable = not block_reasons
    return {
        "quality_passed": quality_passed,
        "video_review_passed": video_review_passed,
        "retention_passed": retention_passed,
        "publishable": publishable,
        "block_reasons": block_reasons,
        "quality_score": payload.get("quality_score"),
        "video_score": payload.get("video_score", review.get("score")),
        "retention_score": payload.get("retention_score", retention_report.get("completion_pct")),
    }


def should_block_live_publish(
    payload: dict[str, Any],
    *,
    mode: str | None = None,
    factory_publish_approved: bool = False,
) -> tuple[bool, dict[str, Any]]:
    """Return (blocked, gate_report). dry_run never blocks; live blocks when QA fails."""
    gate = evaluate_publish_gate(payload)
    normalized = normalize_publish_mode(mode)
    if factory_publish_approved:
        gate["override"] = "factory_publish_approved"
        return False, gate
    if not publish_require_qa():
        gate["qa_enforced"] = False
        return False, gate
    gate["qa_enforced"] = True
    if normalized == "dry_run":
        return False, gate
    if normalized == "live" and not gate["publishable"]:
        return True, gate
    return False, gate
