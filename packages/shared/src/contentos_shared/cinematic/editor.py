"""Cinematic editor settings — zoom, speed ramp, ducking (V5.1.3)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from contentos_shared.providers.ffmpeg_filters import RenderSpec, SceneSegment

CINEMATIC_PRESETS: dict[str, dict[str, Any]] = {
    "default": {
        "enable_zoom": True,
        "enable_ducking": True,
        "music_volume": 0.12,
        "ducking_ratio": 8.0,
        "ducking_threshold": 0.03,
    },
    "dynamic": {
        "enable_zoom": True,
        "enable_ducking": True,
        "music_volume": 0.14,
        "ducking_ratio": 10.0,
        "ducking_threshold": 0.025,
    },
    "calm": {
        "enable_zoom": True,
        "enable_ducking": True,
        "music_volume": 0.1,
        "ducking_ratio": 6.0,
        "ducking_threshold": 0.04,
    },
    "punchy": {
        "enable_zoom": True,
        "enable_ducking": True,
        "music_volume": 0.16,
        "ducking_ratio": 12.0,
        "ducking_threshold": 0.02,
    },
}


@dataclass
class CinematicSettings:
    preset: str = "default"
    enable_zoom: bool = True
    enable_ducking: bool = True
    enable_speed_ramp: bool = True
    music_volume: float = 0.12
    ducking_ratio: float = 8.0
    ducking_threshold: float = 0.03
    fade_duration: float = 0.4

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> CinematicSettings:
        cinematic = (payload or {}).get("cinematic") if isinstance(payload, dict) else None
        if not isinstance(cinematic, dict):
            cinematic = {}
        preset_name = str(
            cinematic.get("preset")
            or os.getenv("CINEMATIC_PRESET", "default")
        ).lower()
        preset = CINEMATIC_PRESETS.get(preset_name, CINEMATIC_PRESETS["default"])
        enabled = os.getenv("ENABLE_CINEMATIC_EDITOR", "true").lower() in ("1", "true", "yes")

        def _flag(key: str, preset_key: str, default: bool) -> bool:
            if key in cinematic:
                return bool(cinematic[key])
            if not enabled:
                return default if key == "enable_zoom" else False
            return bool(preset.get(preset_key, default))

        return cls(
            preset=preset_name,
            enable_zoom=_flag("enable_zoom", "enable_zoom", True),
            enable_ducking=_flag("enable_ducking", "enable_ducking", True),
            enable_speed_ramp=_flag("enable_speed_ramp", "enable_speed_ramp", True),
            music_volume=float(cinematic.get("music_volume", preset.get("music_volume", 0.12))),
            ducking_ratio=float(cinematic.get("ducking_ratio", preset.get("ducking_ratio", 8.0))),
            ducking_threshold=float(
                cinematic.get("ducking_threshold", preset.get("ducking_threshold", 0.03))
            ),
            fade_duration=float(
                cinematic.get("fade_duration", os.getenv("EDITOR_FADE_DURATION", "0.4"))
            ),
        )

    def apply_to_render_spec(self, spec: RenderSpec) -> RenderSpec:
        spec.enable_zoom = self.enable_zoom
        spec.enable_ducking = self.enable_ducking
        spec.music_volume = self.music_volume
        spec.ducking_ratio = self.ducking_ratio
        spec.ducking_threshold = self.ducking_threshold
        spec.fade_duration = self.fade_duration
        return spec


def apply_directive_to_segment(segment: SceneSegment, directive: dict[str, Any] | None) -> SceneSegment:
    if not directive:
        return segment
    if "zoom_enabled" in directive:
        segment.zoom_enabled = bool(directive["zoom_enabled"])
    if directive.get("zoom_max") is not None:
        segment.zoom_max = float(directive["zoom_max"])
    if directive.get("zoom_rate") is not None:
        segment.zoom_rate = float(directive["zoom_rate"])
    if directive.get("pan_x_expr"):
        segment.pan_x_expr = str(directive["pan_x_expr"])
    if directive.get("fade_in") is not None:
        segment.fade_in = float(directive["fade_in"])
    if directive.get("fade_out") is not None:
        segment.fade_out = float(directive["fade_out"])
    if directive.get("crop_bias"):
        segment.crop_bias = str(directive["crop_bias"])
    if directive.get("playback_speed") is not None:
        segment.playback_speed = normalize_playback_speed(directive["playback_speed"])
    if directive.get("speed_ramp_end") is not None:
        segment.speed_ramp_end = normalize_playback_speed(directive["speed_ramp_end"])
    return segment


def normalize_playback_speed(value: Any) -> float:
    try:
        speed = float(value)
    except (TypeError, ValueError):
        return 1.0
    return max(0.5, min(2.0, speed))
