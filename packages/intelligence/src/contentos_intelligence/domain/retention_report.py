"""Retention analysis report — V5.2.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetentionSecond:
    second: int
    retention_pct: float
    scene_label: str = ""
    factors: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "second": self.second,
            "retention_pct": round(self.retention_pct, 2),
            "scene_label": self.scene_label,
            "factors": {k: round(v, 3) for k, v in self.factors.items()},
        }


@dataclass
class RetentionSegment:
    label: str
    start_second: float
    end_second: float
    avg_retention_pct: float
    min_retention_pct: float
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "start_second": round(self.start_second, 2),
            "end_second": round(self.end_second, 2),
            "avg_retention_pct": round(self.avg_retention_pct, 2),
            "min_retention_pct": round(self.min_retention_pct, 2),
            "reason": self.reason,
        }


@dataclass
class RetentionReport:
    overall_score: float
    avg_retention_pct: float
    hook_retention_pct: float
    completion_pct: float
    duration_seconds: float
    drop_seconds: list[int] = field(default_factory=list)
    weak_segments: list[RetentionSegment] = field(default_factory=list)
    timeline: list[RetentionSecond] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    analysis_mode: str = "pre_render"
    quality_score_at_analysis: float | int | None = None
    render_duration_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "avg_retention_pct": round(self.avg_retention_pct, 2),
            "hook_retention_pct": round(self.hook_retention_pct, 2),
            "completion_pct": round(self.completion_pct, 2),
            "duration_seconds": round(self.duration_seconds, 2),
            "drop_seconds": list(self.drop_seconds),
            "weak_segments": [s.to_dict() for s in self.weak_segments],
            "timeline": [t.to_dict() for t in self.timeline],
            "recommendations": list(self.recommendations),
            "analysis_mode": self.analysis_mode,
            "quality_score_at_analysis": self.quality_score_at_analysis,
            "render_duration_seconds": (
                round(self.render_duration_seconds, 2) if self.render_duration_seconds is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> RetentionReport:
        if not data:
            return cls(
                overall_score=0.0,
                avg_retention_pct=0.0,
                hook_retention_pct=0.0,
                completion_pct=0.0,
                duration_seconds=0.0,
            )
        timeline = [
            RetentionSecond(
                second=int(item.get("second", 0)),
                retention_pct=float(item.get("retention_pct") or 0),
                scene_label=str(item.get("scene_label") or ""),
                factors=dict(item.get("factors") or {}),
            )
            for item in data.get("timeline") or []
        ]
        weak = [
            RetentionSegment(
                label=str(item.get("label") or ""),
                start_second=float(item.get("start_second") or 0),
                end_second=float(item.get("end_second") or 0),
                avg_retention_pct=float(item.get("avg_retention_pct") or 0),
                min_retention_pct=float(item.get("min_retention_pct") or 0),
                reason=str(item.get("reason") or ""),
            )
            for item in data.get("weak_segments") or []
        ]
        return cls(
            overall_score=float(data.get("overall_score") or 0),
            avg_retention_pct=float(data.get("avg_retention_pct") or 0),
            hook_retention_pct=float(data.get("hook_retention_pct") or 0),
            completion_pct=float(data.get("completion_pct") or 0),
            duration_seconds=float(data.get("duration_seconds") or 0),
            drop_seconds=[int(s) for s in data.get("drop_seconds") or []],
            weak_segments=weak,
            timeline=timeline,
            recommendations=list(data.get("recommendations") or []),
            analysis_mode=str(data.get("analysis_mode") or "pre_render"),
            quality_score_at_analysis=data.get("quality_score_at_analysis"),
            render_duration_seconds=data.get("render_duration_seconds"),
        )
