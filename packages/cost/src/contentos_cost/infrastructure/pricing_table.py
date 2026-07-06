"""Provider pricing table — USD estimates for text, speech, subtitle, image."""

from __future__ import annotations

# Local providers: zero cost
LOCAL_PROVIDERS = {
    "ollama",
    "piper",
    "local",
    "whisper",
    "qwen",
    "llama",
    "ffmpeg",
    "minio",
    "ffprobe",
    "pillow",
    "llava",
}

# (provider, model) -> {input_per_1k, output_per_1k} for text chat
PRICING_TABLE: dict[tuple[str, str], dict[str, float]] = {
    ("openai", "gpt-4o"): {"input_per_1k": 0.0025, "output_per_1k": 0.01},
    ("openai", "gpt-4o-mini"): {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
    ("openai", "whisper-1"): {"input_per_1k": 0.006, "output_per_1k": 0.0},
    ("claude", "claude-3-5-sonnet-20241022"): {"input_per_1k": 0.003, "output_per_1k": 0.015},
    ("gemini", "gemini-1.5-flash"): {"input_per_1k": 0.000075, "output_per_1k": 0.0003},
    ("deepseek", "deepseek-chat"): {"input_per_1k": 0.00014, "output_per_1k": 0.00028},
    ("mistral", "mistral-small-latest"): {"input_per_1k": 0.001, "output_per_1k": 0.003},
    ("elevenlabs", "eleven_multilingual_v2"): {"input_per_1k": 0.0, "output_per_1k": 0.0},
}

# Speech: USD per 1K characters
SPEECH_PRICING_PER_1K_CHARS: dict[str, float] = {
    "elevenlabs": 0.30,
    "openai": 0.015,
}

# Subtitle / STT: USD per audio minute (estimated from bytes if duration unknown)
SUBTITLE_PRICING_PER_MINUTE: dict[str, float] = {
    "openai": 0.006,
}

# Image: USD per image
IMAGE_PRICING_PER_IMAGE: dict[str, float] = {
    "openai": 0.04,
}


def estimate_cost_usd(
    provider: str,
    model: str,
    tokens_input: int,
    tokens_output: int,
    *,
    from_cache: bool = False,
) -> float:
    if from_cache:
        return 0.0
    key = provider.lower()
    if key in LOCAL_PROVIDERS:
        return 0.0
    rates = PRICING_TABLE.get((key, model)) or PRICING_TABLE.get((key, "*"))
    if not rates:
        return 0.0
    cost = (tokens_input / 1000.0) * rates.get("input_per_1k", 0.0)
    cost += (tokens_output / 1000.0) * rates.get("output_per_1k", 0.0)
    return round(cost, 6)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_speech_cost_usd(provider: str, char_count: int) -> float:
    key = provider.lower()
    if key in LOCAL_PROVIDERS or char_count <= 0:
        return 0.0
    rate = SPEECH_PRICING_PER_1K_CHARS.get(key, 0.0)
    return round((char_count / 1000.0) * rate, 6)


def estimate_subtitle_cost_usd(
    provider: str,
    *,
    audio_bytes: int = 0,
    duration_seconds: float | None = None,
) -> float:
    key = provider.lower()
    if key in LOCAL_PROVIDERS:
        return 0.0
    rate = SUBTITLE_PRICING_PER_MINUTE.get(key, 0.0)
    if duration_seconds and duration_seconds > 0:
        minutes = duration_seconds / 60.0
    elif audio_bytes > 0:
        # ~16KB/s rough for mp3 narration
        minutes = max(audio_bytes / (16_000 * 60), 0.01)
    else:
        return 0.0
    return round(minutes * rate, 6)


def estimate_image_cost_usd(provider: str, image_count: int = 1) -> float:
    key = provider.lower()
    if key in LOCAL_PROVIDERS or image_count <= 0:
        return 0.0
    rate = IMAGE_PRICING_PER_IMAGE.get(key, 0.0)
    return round(rate * image_count, 6)


def estimate_audio_minutes(audio_bytes: int, duration_seconds: float | None = None) -> float:
    if duration_seconds and duration_seconds > 0:
        return duration_seconds / 60.0
    if audio_bytes <= 0:
        return 0.0
    return max(audio_bytes / (16_000 * 60), 0.01)
