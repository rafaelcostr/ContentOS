"""Visual intelligence read models for Autopilot.

The visual layer summarizes already analyzed assets and quality signals. It does
not run media analysis, edit video, render, or call AI Director.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

Pacing = Literal["slow", "medium", "fast"]


@dataclass(frozen=True)
class VisualPatternSnapshot:
    project_id: str
    channel_id: str | None
    confidence: Literal["low", "medium", "high"]
    score: int
    summary: str
    sample_size: int = 0
    pacing: Pacing = "medium"
    movements: list[str] = field(default_factory=list)
    transitions: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    scenarios: list[str] = field(default_factory=list)
    framings: list[str] = field(default_factory=list)
    emotions: list[str] = field(default_factory=list)
    typography: dict[str, Any] = field(default_factory=dict)
    subtitle_style: dict[str, Any] = field(default_factory=dict)
    editor_hints: dict[str, Any] = field(default_factory=dict)
    creative_hints: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "channel_id": self.channel_id,
            "confidence": self.confidence,
            "score": self.score,
            "summary": self.summary,
            "sample_size": self.sample_size,
            "pacing": self.pacing,
            "movements": list(self.movements),
            "transitions": list(self.transitions),
            "colors": list(self.colors),
            "scenarios": list(self.scenarios),
            "framings": list(self.framings),
            "emotions": list(self.emotions),
            "typography": dict(self.typography),
            "subtitle_style": dict(self.subtitle_style),
            "editor_hints": dict(self.editor_hints),
            "creative_hints": list(self.creative_hints),
            "risks": list(self.risks),
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _top(counter: Counter[str], *, limit: int = 8) -> list[str]:
    return [item for item, _count in counter.most_common(limit) if item]


def _add(counter: Counter[str], value: Any) -> None:
    text = str(value or "").strip().lower()
    if text:
        counter[text] += 1


def _add_many(counter: Counter[str], values: Any) -> None:
    for item in _as_list(values):
        _add(counter, item)


def _pacing(motions: Counter[str], speeds: Counter[str], sample_size: int) -> Pacing:
    fast_words = {"fast", "rapido", "rápido", "speed", "dynamic", "dinamico", "dinâmico"}
    slow_words = {"slow", "lento", "calm", "estatico", "estático", "static"}
    fast = sum(count for key, count in {**motions, **speeds}.items() if key in fast_words or "fast" in key)
    slow = sum(count for key, count in {**motions, **speeds}.items() if key in slow_words or "slow" in key)
    if sample_size and fast / sample_size >= 0.35:
        return "fast"
    if sample_size and slow / sample_size >= 0.45:
        return "slow"
    return "medium"


def _movement_hints(motions: Counter[str], pacing: Pacing) -> list[str]:
    top_motions = _top(motions, limit=4)
    hints: list[str] = []
    if any("pan" in item for item in top_motions):
        hints.append("pan-left")
    if any("zoom" in item for item in top_motions):
        hints.append("zoom-in")
    if pacing == "fast":
        hints.extend(["cut", "speed-ramp-up"])
    elif pacing == "slow":
        hints.extend(["fade", "ken-burns"])
    else:
        hints.extend(["ken-burns", "fade"])
    out: list[str] = []
    for hint in hints:
        if hint not in out:
            out.append(hint)
    return out[:6]


def build_visual_pattern_snapshot(
    *,
    project_id: str,
    channel_id: str | None = None,
    media_profiles: list[Mapping[str, Any] | Any] | None = None,
    video_reviews: list[Mapping[str, Any] | Any] | None = None,
    retention_reports: list[Mapping[str, Any] | Any] | None = None,
) -> VisualPatternSnapshot:
    scenarios: Counter[str] = Counter()
    motions: Counter[str] = Counter()
    speeds: Counter[str] = Counter()
    angles: Counter[str] = Counter()
    colors: Counter[str] = Counter()
    emotions: Counter[str] = Counter()
    camera_types: Counter[str] = Counter()

    profiles = [_as_dict(profile) for profile in _as_list(media_profiles or [])]
    for profile in profiles:
        analysis = _as_dict(profile.get("analysis") or profile)
        _add(scenarios, analysis.get("scenario"))
        _add(motions, analysis.get("motion"))
        _add(speeds, analysis.get("speed"))
        _add(angles, analysis.get("angle"))
        _add(emotions, analysis.get("emotion"))
        _add(camera_types, analysis.get("camera_type"))
        _add_many(colors, analysis.get("colors"))

    sample_size = len(profiles)
    pacing = _pacing(motions, speeds, sample_size)
    movement_hints = _movement_hints(motions, pacing)
    review_rows = [_as_dict(row) for row in _as_list(video_reviews or [])]
    retention_rows = [_as_dict(row) for row in _as_list(retention_reports or [])]
    risks: list[str] = []
    if sample_size == 0:
        risks.append("Nenhum AssetMediaProfile disponível. Rode media_analyze nos assets para elevar a confiança visual.")
    if any(str(row.get("passed")).lower() == "false" for row in review_rows):
        risks.append("Há revisões de vídeo reprovadas que podem indicar problema visual.")
    if any(float(row.get("completion_pct") or row.get("avg_retention_pct") or 100) < 45 for row in retention_rows):
        risks.append("Relatórios de retenção indicam possível queda por ritmo/visual.")

    confidence: Literal["low", "medium", "high"] = "high" if sample_size >= 12 else "medium" if sample_size >= 4 else "low"
    score = min(100, 35 + sample_size * 5 + (10 if not risks else 0))
    top_scenarios = _top(scenarios, limit=6)
    top_colors = _top(colors, limit=8)
    top_emotions = _top(emotions, limit=6)
    summary = (
        f"{sample_size} asset(s) analisado(s), ritmo {pacing}, "
        f"cenários principais: {', '.join(top_scenarios[:3]) or 'indefinidos'}."
    )

    return VisualPatternSnapshot(
        project_id=project_id,
        channel_id=channel_id,
        confidence=confidence,
        score=score,
        summary=summary,
        sample_size=sample_size,
        pacing=pacing,
        movements=movement_hints,
        transitions=["cut", "fade"] if pacing == "fast" else ["fade", "dissolve"],
        colors=top_colors,
        scenarios=top_scenarios,
        framings=_top(angles, limit=6) or _top(camera_types, limit=6),
        emotions=top_emotions,
        typography={
            "caption_weight": "bold" if pacing == "fast" else "regular",
            "overlay_density": "high" if pacing == "fast" else "medium",
        },
        subtitle_style={
            "max_words_per_line": 4 if pacing == "fast" else 6,
            "safe_area": "lower_third",
            "avoid_full_screen_blocks": True,
        },
        editor_hints={
            "pacing": pacing,
            "preferred_movements": movement_hints,
            "preferred_transitions": ["cut", "fade"] if pacing == "fast" else ["fade", "dissolve"],
            "prefer_zoom_cuts": pacing != "slow",
            "color_palette": top_colors[:5],
        },
        creative_hints=[
            "Manter legendas em blocos curtos e sem ocupar a tela inteira.",
            "Usar movimento visual coerente com os assets mais fortes.",
            "Ajustar cortes ao ritmo previsto antes do editor.",
        ],
        risks=risks,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
