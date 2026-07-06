"""Director plan — storyboard frames → FFmpeg render parameters (V3 Tier B5)."""

from __future__ import annotations

from contentos_shared.payload_utils import coerce_dict

PACING_LEVELS = ("slow", "medium", "fast")
MOVEMENTS = ("static", "zoom-in", "zoom-out", "pan-left", "pan-right", "ken-burns")
TRANSITIONS = ("cut", "fade", "dissolve")
FRAMINGS = ("close-up", "medium", "wide")
CROP_BIASES = ("top", "center", "bottom")

_TRANSITION_FADE = {"cut": 0.15, "fade": 0.45, "dissolve": 0.65}
_FRAMING_CROP = {"close-up": "top", "medium": "center", "wide": "center"}
_MOVEMENT_ZOOM = {
    "static": (False, 1.0, 0.0),
    "zoom-in": (True, 1.18, 0.0008),
    "zoom-out": (True, 1.06, 0.00035),
    "pan-left": (True, 1.08, 0.00045),
    "pan-right": (True, 1.08, 0.00045),
    "ken-burns": (True, 1.12, 0.0006),
}
_PAN_X = {
    "pan-left": "max(0\\,iw/2-(iw/zoom/2)-on*1.5)",
    "pan-right": "min(iw-iw/zoom\\,iw/2-(iw/zoom/2)+on*1.5)",
}


def _pick(value: str, allowed: tuple[str, ...], default: str) -> str:
    text = str(value or "").lower().strip().replace("_", "-")
    return text if text in allowed else default


def _pacing_from_emotion(emotion: dict) -> tuple[str, int]:
    overall = emotion.get("overall") or emotion.get("emotion") or 5
    try:
        score = int(round(float(overall)))
    except (TypeError, ValueError):
        score = 5
    score = max(1, min(10, score))
    if score >= 8:
        return "fast", score
    if score <= 4:
        return "slow", score
    return "medium", score


def _fade_for_transition(transition: str, pacing: str) -> tuple[float, float]:
    base = _TRANSITION_FADE.get(transition, 0.45)
    if pacing == "fast":
        base *= 0.7
    elif pacing == "slow":
        base *= 1.25
    fade_in = max(0.1, min(base, 1.0))
    fade_out = fade_in
    return fade_in, fade_out


def frame_to_directive(frame: dict, *, pacing: str) -> dict:
    movement = _pick(frame.get("movement", ""), MOVEMENTS, "ken-burns")
    transition = _pick(frame.get("transition", ""), TRANSITIONS, "fade")
    framing = _pick(frame.get("framing", ""), FRAMINGS, "medium")
    zoom_enabled, zoom_max, zoom_rate = _MOVEMENT_ZOOM.get(movement, _MOVEMENT_ZOOM["ken-burns"])
    fade_in, fade_out = _fade_for_transition(transition, pacing)

    if framing == "close-up" and zoom_enabled:
        zoom_max = min(zoom_max + 0.04, 1.22)
        zoom_rate = min(zoom_rate + 0.00015, 0.001)

    directive: dict = {
        "scene_index": int(frame.get("scene_index", 0)),
        "scene_label": str(frame.get("scene_label") or f"scene_{frame.get('scene_index', 0)}"),
        "duration_seconds": max(float(frame.get("duration_seconds") or 3.0), 1.0),
        "movement": movement,
        "transition": transition,
        "framing": framing,
        "crop_bias": _FRAMING_CROP.get(framing, "center"),
        "zoom_enabled": zoom_enabled,
        "zoom_max": round(zoom_max, 4),
        "zoom_rate": round(zoom_rate, 6),
        "fade_in": round(fade_in, 3),
        "fade_out": round(fade_out, 3),
    }
    if movement in _PAN_X:
        directive["pan_x_expr"] = _PAN_X[movement]
    return directive


def _frames_from_scenes(scenes: list[dict]) -> list[dict]:
    frames: list[dict] = []
    for i, scene in enumerate(scenes):
        start = float(scene.get("start_seconds", i * 5))
        end = float(scene.get("end_seconds", start + 5))
        frames.append(
            {
                "scene_index": i,
                "scene_label": str(scene.get("label") or f"scene_{i}"),
                "framing": "medium",
                "movement": "ken-burns",
                "transition": "fade",
                "duration_seconds": max(end - start, 1.0),
            }
        )
    return frames


def build_director_plan(
    *,
    storyboard: dict | None,
    scenes: list[dict],
    emotion: dict | None = None,
) -> dict:
    """Translate storyboard frames + emotion into editor-ready render directives."""
    board = coerce_dict(storyboard)
    emotion_data = coerce_dict(emotion)
    pacing, energy = _pacing_from_emotion(emotion_data)

    frames = board.get("frames")
    if not isinstance(frames, list) or not frames:
        frames = _frames_from_scenes(scenes)

    directives = [frame_to_directive(coerce_dict(f), pacing=pacing) for f in frames]
    if scenes and len(directives) < len(scenes):
        extra = _frames_from_scenes(scenes[len(directives) :])
        directives.extend(frame_to_directive(coerce_dict(f), pacing=pacing) for f in extra)

    default_fade = _TRANSITION_FADE["fade"]
    if pacing == "fast":
        default_fade *= 0.7
    elif pacing == "slow":
        default_fade *= 1.25

    return {
        "pacing": pacing,
        "energy": energy,
        "default_fade": round(default_fade, 3),
        "overall_style": str(board.get("overall_style") or "vertical dinâmico"),
        "segments": directives[: max(len(scenes), 1)],
    }


def directive_for_index(director_plan: dict | None, index: int) -> dict | None:
    if not director_plan:
        return None
    segments = director_plan.get("segments")
    if not isinstance(segments, list) or index >= len(segments):
        return None
    return coerce_dict(segments[index])
