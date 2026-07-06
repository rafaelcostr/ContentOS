"""Provider registry — maps keys to adapter class paths."""

TEXT_REGISTRY: dict[str, str] = {
    "ollama": "contentos_ai.infrastructure.adapters.text.ollama.OllamaTextAdapter",
    "openai": "contentos_ai.infrastructure.adapters.text.openai.OpenAITextAdapter",
    "claude": "contentos_ai.infrastructure.adapters.text.claude.ClaudeTextAdapter",
    "gemini": "contentos_ai.infrastructure.adapters.text.gemini.GeminiTextAdapter",
    "deepseek": "contentos_ai.infrastructure.adapters.text.deepseek.DeepSeekTextAdapter",
    "mistral": "contentos_ai.infrastructure.adapters.text.mistral.MistralTextAdapter",
    "qwen": "contentos_ai.infrastructure.adapters.text.ollama.OllamaTextAdapter",
    "llama": "contentos_ai.infrastructure.adapters.text.ollama.OllamaTextAdapter",
}

SPEECH_REGISTRY: dict[str, str] = {
    "piper": "contentos_ai.infrastructure.adapters.speech.piper.PiperSpeechAdapter",
    "elevenlabs": "contentos_ai.infrastructure.adapters.speech.elevenlabs.ElevenLabsSpeechAdapter",
}

SUBTITLE_REGISTRY: dict[str, str] = {
    "local": "contentos_ai.infrastructure.adapters.subtitle.whisper.WhisperSubtitleAdapter",
    "whisper": "contentos_ai.infrastructure.adapters.subtitle.whisper.WhisperSubtitleAdapter",
    "openai": "contentos_ai.infrastructure.adapters.subtitle.openai_whisper.OpenAIWhisperAdapter",
}

IMAGE_REGISTRY: dict[str, str] = {
    "local": "contentos_ai.infrastructure.adapters.image.local.LocalImageAdapter",
    "pillow": "contentos_ai.infrastructure.adapters.image.local.LocalImageAdapter",
}

VISION_REGISTRY: dict[str, str] = {
    "ollama": "contentos_ai.infrastructure.adapters.vision.ollama.OllamaVisionAdapter",
    "llava": "contentos_ai.infrastructure.adapters.vision.ollama.OllamaVisionAdapter",
}

EMBEDDING_REGISTRY: dict[str, str] = {
    "ollama": "contentos_ai.infrastructure.adapters.embedding.ollama.OllamaEmbeddingAdapter",
}
