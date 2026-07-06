"""Backward compatibility — use contentos_shared.providers.speech.elevenlabs instead."""

from contentos_shared.providers.speech.elevenlabs import ElevenLabsSpeechProvider as ElevenLabsProvider

__all__ = ["ElevenLabsProvider"]
