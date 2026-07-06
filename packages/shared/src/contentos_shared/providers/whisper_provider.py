"""Backward compatibility — use contentos_shared.providers.subtitle.openai_whisper instead."""

from contentos_shared.providers.subtitle.openai_whisper import OpenAIWhisperProvider as WhisperProvider

__all__ = ["WhisperProvider"]
