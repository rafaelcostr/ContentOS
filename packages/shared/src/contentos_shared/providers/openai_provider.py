"""Backward compatibility — use contentos_shared.providers.ai.openai instead."""

from contentos_shared.providers.ai.openai import OpenAITextProvider as OpenAIProvider

__all__ = ["OpenAIProvider"]
