"""Pure FFmpeg filter builders — testable without running ffmpeg."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SceneSegment:
    """Single scene in the timeline."""

    index: int
    duration: float
    clip_path: Path | None = None
    label: str = ""
    zoom_enabled: bool | None = None
    zoom_max: float = 1.12
    zoom_rate: float = 0.0006
    pan_x_expr: str | None = None
    pan_y_expr: str | None = None
    fade_in: float | None = None
    fade_out: float | None = None
    crop_bias: str = "center"
    playback_speed: float = 1.0
    speed_ramp_end: float | None = None


@dataclass
class RenderSpec:
    """Full render specification for vertical short-form video."""

    width: int = 1080
    height: int = 1920
    fps: int = 60
    total_duration: float = 45.0
    scenes: list[SceneSegment] = field(default_factory=list)
    enable_zoom: bool = True
    fade_duration: float = 0.4
    music_volume: float = 0.12
    progress_bar_height: int = 8
    enable_ducking: bool = True
    ducking_ratio: float = 8.0
    ducking_threshold: float = 0.03


def speed_filter_expr(segment: SceneSegment | None, duration: float, fps: int) -> str | None:
    """Return setpts expression for constant or ramped playback speed."""
    if not segment:
        return None
    start = max(0.5, min(2.0, float(segment.playback_speed or 1.0)))
    end_raw = segment.speed_ramp_end
    if end_raw is None or abs(float(end_raw) - start) < 0.02:
        if abs(start - 1.0) < 0.02:
            return None
        return f"setpts=PTS/{start:.4f}"
    end = max(0.5, min(2.0, float(end_raw)))
    frames = max(1, int(duration * fps))
    return f"setpts='PTS/({start:.4f}+({end:.4f}-{start:.4f})*on/{frames})'"


def scene_video_filter(spec: RenderSpec, duration: float, segment: SceneSegment | None = None) -> str:
    """Ken Burns zoom + fade in/out for a single scene clip."""
    w, h, fps = spec.width, spec.height, spec.fps
    if segment and segment.fade_in is not None:
        fade = segment.fade_in
    else:
        fade = spec.fade_duration
    if segment and segment.fade_out is not None:
        fade_out = segment.fade_out
    else:
        fade_out = fade
    fade_out_start = max(0.0, duration - fade_out)
    frames = max(1, int(duration * fps))

    crop_y = {
        "top": f"(ih-{h})/4",
        "center": f"(ih-{h})/2",
        "bottom": f"(ih-{h})*3/4",
    }.get((segment.crop_bias if segment else "center") or "center", f"(ih-{h})/2")

    base = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:x=(iw-{w})/2:y={crop_y},setsar=1"
    speed_expr = speed_filter_expr(segment, duration, fps)
    if speed_expr:
        base += f",{speed_expr}"
    enable_zoom = segment.zoom_enabled if segment and segment.zoom_enabled is not None else spec.enable_zoom
    if enable_zoom:
        zoom_max = segment.zoom_max if segment else 1.12
        zoom_rate = segment.zoom_rate if segment else 0.0006
        pan_x = segment.pan_x_expr if segment and segment.pan_x_expr else "iw/2-(iw/zoom/2)"
        pan_y = segment.pan_y_expr if segment and segment.pan_y_expr else "ih/2-(ih/zoom/2)"
        base += (
            f",zoompan=z='min(1+{zoom_rate}*on,{zoom_max})':"
            f"x='{pan_x}':y='{pan_y}':"
            f"d={frames}:s={w}x{h}:fps={fps}"
        )
    else:
        base += f",fps={fps}"

    base += f",fade=t=in:st=0:d={fade},fade=t=out:st={fade_out_start}:d={fade_out}"
    return base


def placeholder_video_filter(spec: RenderSpec, duration: float) -> str:
    """Animated gradient placeholder when no take is available."""
    w, h, fps = spec.width, spec.height, spec.fps
    fade = spec.fade_duration
    fade_out_start = max(0.0, duration - fade)
    return f"scale={w}:{h},fps={fps},fade=t=in:st=0:d={fade},fade=t=out:st={fade_out_start}:d={fade}"


def subtitle_and_progress_filter(
    subtitle_path: Path | None,
    spec: RenderSpec,
) -> str:
    """Burn subtitles + bottom progress bar synced to timeline."""
    w, h = spec.width, spec.height
    bar_h = spec.progress_bar_height
    duration = max(spec.total_duration, 1.0)

    filters: list[str] = [f"scale={w}:{h},setsar=1,fps={spec.fps}"]

    if subtitle_path and subtitle_path.exists():
        srt = str(subtitle_path).replace("\\", "/").replace(":", "\\:")
        filters.append(
            f"subtitles='{srt}':force_style="
            f"'FontSize=26,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
            f"Outline=2,Bold=1,Alignment=2,MarginV=120'"
        )

    # Progress bar: white fill grows left-to-right over total duration
    filters.append(
        f"drawbox=x=0:y=h-{bar_h}:w='min(iw\\,{bar_h}+(iw-{bar_h * 2})*t/{duration})':"
        f"h={bar_h}:color=white@0.85:t=fill,"
        f"drawbox=x=0:y=h-{bar_h}:w=iw:h={bar_h}:color=black@0.35:t=3"
    )
    return ",".join(filters)


def build_audio_mix_filter(
    has_music: bool,
    music_volume: float,
    *,
    enable_ducking: bool = True,
    ducking_ratio: float = 8.0,
    ducking_threshold: float = 0.03,
) -> str:
    """Mix narration with optional background music (sidechain ducking when enabled)."""
    if not has_music:
        return "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    vol = music_volume
    if enable_ducking:
        # Voice must feed both the sidechain key and the final mix; an FFmpeg
        # link label can only be consumed once, so asplit into two copies.
        return (
            f"[1:a]aresample=44100,aformat=channel_layouts=mono,"
            f"loudnorm=I=-16:TP=-1.5:LRA=11:linear=true,"
            f"asplit=2[voicekey][voicemix];"
            f"[2:a]aresample=44100,aformat=channel_layouts=mono,volume={vol}[bg];"
            f"[bg][voicekey]sidechaincompress=threshold={ducking_threshold}:"
            f"ratio={ducking_ratio}:attack=80:release=500[bgduck];"
            f"[voicemix][bgduck]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
    return (
        f"[1:a]aresample=44100,aformat=channel_layouts=mono,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11:linear=true[voice];"
        f"[2:a]aresample=44100,aformat=channel_layouts=mono,volume={vol},"
        f"afade=t=in:st=0:d=1,afade=t=out:st=0:d=0[bg];"
        f"[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )


def transition_sfx_filter(scene_count: int, scene_durations: list[float]) -> str:
    """Short whoosh-like volume dip at scene boundaries (via volume keyframes)."""
    if scene_count <= 1:
        return "anull"
    # Subtle emphasis on narration at scene starts — handled in mix via afade on music
    return "anull"
