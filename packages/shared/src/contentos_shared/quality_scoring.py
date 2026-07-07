"""Technical quality scoring 0–10 for render validation (post-Tier E)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityDimension:
    name: str
    score: int
    passed: bool
    detail: str = ""


@dataclass
class QualityReport:
    score: int
    passed: bool
    min_score: int
    dimensions: dict[str, int]
    errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "quality_score": self.score,
            "quality_passed": self.passed,
            "quality_min_score": self.min_score,
            "quality_dimensions": self.dimensions,
            "quality_errors": self.errors,
            "quality_suggestions": self.suggestions,
        }


def quality_min_score() -> int:
    try:
        return max(0, min(10, int(os.getenv("QUALITY_MIN_SCORE", "6"))))
    except ValueError:
        return 6


def quality_min_bitrate_bps() -> int:
    try:
        return max(0, int(os.getenv("QUALITY_MIN_BITRATE_BPS", "1000000")))
    except ValueError:
        return 1_000_000


def _dim(name: str, passed: bool, *, detail: str = "", partial_score: int | None = None) -> QualityDimension:
    if partial_score is not None:
        score = max(0, min(10, partial_score))
        return QualityDimension(name=name, score=score, passed=score >= 6, detail=detail)
    score = 10 if passed else 0
    return QualityDimension(name=name, score=score, passed=passed, detail=detail)


def score_framerate(fps: float) -> QualityDimension:
    if fps >= 55:
        return _dim("framerate", True, detail=f"{fps:.1f}fps")
    if fps >= 30:
        return _dim("framerate", False, detail=f"{fps:.1f}fps (below 60)", partial_score=5)
    return _dim("framerate", False, detail=f"{fps:.1f}fps (too low)", partial_score=0)


def score_duration(duration: float) -> QualityDimension:
    if 15 <= duration <= 60:
        return _dim("duration", True, detail=f"{duration:.1f}s")
    if 0 < duration < 15:
        return _dim("duration", False, detail=f"{duration:.1f}s (short)", partial_score=6)
    if 60 < duration <= 90:
        return _dim("duration", False, detail=f"{duration:.1f}s (long)", partial_score=4)
    return _dim("duration", False, detail=f"{duration:.1f}s", partial_score=0)


def build_quality_report(
    *,
    has_render: bool,
    render_exists: bool,
    render_size_ok: bool,
    has_audio_ref: bool,
    has_audio_stream: bool,
    has_subtitles: bool,
    subtitle_sync_skipped: bool,
    width: int = 0,
    height: int = 0,
    codec: str = "",
    fps: float = 0.0,
    duration: float = 0.0,
    has_real_clips: bool | None = None,
    missing_clip_count: int = 0,
    has_narration_audio: bool | None = None,
    subtitle_sync_ok: bool | None = None,
    bit_rate: int | None = None,
    extra_errors: list[str] | None = None,
) -> QualityReport:
    """Aggregate technical checks into a 0–10 score and pass/fail."""
    errors = list(extra_errors or [])
    dims: list[QualityDimension] = []

    integrity_ok = has_render and render_exists and render_size_ok
    dims.append(
        _dim(
            "integrity",
            integrity_ok,
            detail="render present" if integrity_ok else "missing or corrupt render",
        )
    )
    if not has_render:
        errors.append("Missing render video")
    elif not render_exists:
        errors.append("Render file missing in storage")
    elif not render_size_ok:
        errors.append("Render file corrupt or too small")

    res_ok = width == 1080 and height == 1920
    dims.append(
        _dim(
            "resolution",
            res_ok,
            detail=f"{width}x{height}" if width else "unknown",
        )
    )
    if width and height and not res_ok:
        errors.append(f"Invalid resolution: {width}x{height} (expected 1080x1920)")

    codec_ok = codec in ("h264", "avc1", "")
    if codec and codec not in ("h264", "avc1"):
        codec_ok = False
        errors.append(f"Invalid codec: {codec} (expected h264)")
    dims.append(_dim("codec", codec_ok or not codec, detail=codec or "n/a"))

    if fps > 0:
        dims.append(score_framerate(fps))
    elif has_render and render_exists:
        dims.append(_dim("framerate", False, detail="unknown fps"))
        errors.append("Could not read framerate")

    audio_ok = has_audio_ref and has_audio_stream
    dims.append(_dim("audio", audio_ok, detail="audio stream ok" if audio_ok else "missing audio"))
    if not has_audio_ref:
        errors.append("Missing narration audio")
    elif not has_audio_stream:
        errors.append("No audio stream in render")

    if duration > 0:
        dims.append(score_duration(duration))
    elif has_render and render_exists:
        dims.append(_dim("duration", False, detail="zero duration"))
        errors.append("Zero duration video")
    elif duration > 60:
        errors.append(f"Duration exceeds 60s: {duration:.1f}s")

    sub_ok = has_subtitles or subtitle_sync_skipped
    if subtitle_sync_ok is False:
        sub_ok = False
        errors.append("Subtitle timing out of sync with segment list")
    dims.append(
        _dim(
            "subtitles",
            sub_ok,
            detail="subtitles present" if has_subtitles else ("sync skipped" if subtitle_sync_skipped else "missing"),
        )
    )
    if not has_subtitles and not subtitle_sync_skipped:
        errors.append("Missing subtitles")
    if subtitle_sync_ok is False:
        dims.append(_dim("subtitle_sync", False, detail="SRT drift exceeds tolerance"))

    if bit_rate is not None and bit_rate > 0:
        min_bitrate = quality_min_bitrate_bps()
        bitrate_ok = bit_rate >= min_bitrate
        dims.append(
            _dim(
                "bitrate",
                bitrate_ok,
                detail=f"{bit_rate // 1000}kbps" if bitrate_ok else f"{bit_rate // 1000}kbps (<{min_bitrate // 1000}kbps)",
            )
        )
        if not bitrate_ok:
            errors.append(f"Bitrate below minimum: {bit_rate} bps")

    if has_real_clips is not None:
        dims.append(
            _dim(
                "real_clips",
                has_real_clips,
                detail="all scenes use real clips" if has_real_clips else f"{missing_clip_count} placeholder scenes",
            )
        )

    if has_narration_audio is not None:
        dims.append(
            _dim(
                "narration",
                has_narration_audio,
                detail="narration audio present" if has_narration_audio else "silent/generated audio",
            )
        )

    if dims:
        score = round(sum(d.score for d in dims) / len(dims))
    else:
        score = 0

    critical = not integrity_ok or not has_audio_ref or not has_render
    if critical:
        score = min(score, 3)

    min_score = quality_min_score()
    passed = score >= min_score and not critical and not errors

    suggestions: list[str] = []
    dim_map = {d.name: d for d in dims}
    if dim_map.get("resolution") and not dim_map["resolution"].passed:
        suggestions.append("Re-export em 1080x1920 vertical")
    if dim_map.get("framerate") and not dim_map["framerate"].passed:
        suggestions.append("Aumentar framerate para ~60fps no editor")
    if dim_map.get("duration") and not dim_map["duration"].passed:
        suggestions.append("Ajustar duração entre 15s e 60s")
    if dim_map.get("subtitles") and not dim_map["subtitles"].passed:
        suggestions.append("Regenerar legendas sincronizadas")
    if dim_map.get("subtitle_sync") and not dim_map["subtitle_sync"].passed:
        suggestions.append("Revisar timestamps SRT vs segmentos de narração")
    if dim_map.get("bitrate") and not dim_map["bitrate"].passed:
        suggestions.append("Aumentar bitrate do render (CRF/preset no editor)")
    if dim_map.get("real_clips") and not dim_map["real_clips"].passed:
        suggestions.append("Substituir cenas placeholder por clipes reais")
    if dim_map.get("narration") and not dim_map["narration"].passed:
        suggestions.append("Regenerar narração antes do render final")
    if critical:
        suggestions.append("Re-renderizar vídeo no editor antes de continuar")

    return QualityReport(
        score=max(0, min(10, score)),
        passed=passed,
        min_score=min_score,
        dimensions={d.name: d.score for d in dims},
        errors=errors,
        suggestions=suggestions,
    )
