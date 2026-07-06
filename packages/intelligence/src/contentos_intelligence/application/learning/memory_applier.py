"""Apply learning signals to project memory — Epic 7."""

from __future__ import annotations

import os

from contentos_memory.domain.project_memory import ProjectMemoryData

from contentos_intelligence.domain.learning import LearningReport


def _min_content_score() -> float:
    return float(os.getenv("LEARNING_MIN_CONTENT_SCORE", "55"))


def _min_viral_score() -> float:
    return float(os.getenv("LEARNING_MIN_VIRAL_SCORE", "6.5"))


def _should_apply(report: LearningReport) -> bool:
    if report.content_score is not None and report.content_score >= _min_content_score():
        return True
    if report.viral_score is not None and report.viral_score >= _min_viral_score():
        return True
    return False


def _dedupe_prepend(items: list[str], value: str, *, limit: int = 10) -> list[str]:
    cleaned = value.strip()
    if not cleaned:
        return list(items)
    rest = [item for item in items if item != cleaned]
    return [cleaned, *rest][:limit]


def apply_to_memory(memory: ProjectMemoryData, report: LearningReport) -> list[str]:
    """Mutates memory in place; returns list of applied update labels."""
    if not _should_apply(report):
        return []

    updates: list[str] = []
    topic = report.topic or "pipeline"

    if report.hook_text:
        memory.hook_patterns = _dedupe_prepend(memory.hook_patterns, report.hook_text, limit=12)
        if not memory.hook_style:
            memory.hook_style = report.hook_text[:120]
        updates.append("hook_patterns")

    if report.cta_text:
        memory.cta = report.cta_text
        updates.append("cta")

    for signal in report.signals:
        if signal.signal_type != "specialist":
            continue
        name = str(signal.metadata.get("name") or "").strip()
        if name and not memory.niche:
            memory.niche = name
            updates.append("niche")
        context = str(signal.metadata.get("context") or "").strip()
        if context and not memory.goal:
            memory.goal = context[:200]
            updates.append("goal")

    summary_bits = [f"{topic}"]
    if report.content_score is not None:
        summary_bits.append(f"score={report.content_score:.0f}")
    if report.viral_score is not None:
        summary_bits.append(f"viral={report.viral_score:.1f}")
    entry = {
        "pipeline_id": report.pipeline_id,
        "summary": " · ".join(summary_bits),
        "content_score": report.content_score,
        "viral_score": report.viral_score,
        "specialist_id": report.specialist_id,
        "hook": report.hook_text[:200] if report.hook_text else None,
    }
    memory.history = [entry, *(memory.history or [])][:10]
    updates.append("history")

    report.memory_applied = True
    report.memory_updates = updates
    return updates
