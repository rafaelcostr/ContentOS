"""Default per-agent model configuration (env-aware)."""

import os

DEFAULT_AGENT_MODELS: dict[str, dict[str, str]] = {
    "trend_intelligence": {"provider_type": "compute", "provider": "rules", "model_env": "", "default_model": "memory+analytics"},
    "research": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "hook": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "script": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "script_review": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "emotion": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "content_intelligence": {"provider_type": "compute", "provider": "rules", "model_env": "", "default_model": "viral+reuse"},
    "video_review": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "storyboard": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "scene_director": {"provider_type": "compute", "provider": "rules", "model_env": "", "default_model": "storyboard-mapper"},
    "scene": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "publisher": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "analytics": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "thumbnail": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "clip_research": {"provider_type": "text", "provider": "ollama", "model_env": "OLLAMA_MODEL", "default_model": "qwen2.5:7b"},
    "voice": {"provider_type": "speech", "provider": "piper", "model_env": "PIPER_VOICE", "default_model": "pt_BR-faber-medium"},
    "subtitle": {"provider_type": "subtitle", "provider": "local", "model_env": "WHISPER_MODEL", "default_model": "large-v3"},
    "editor": {"provider_type": "compute", "provider": "ffmpeg", "model_env": "", "default_model": "libx264 1080x1920@60"},
    "takes": {"provider_type": "compute", "provider": "minio", "model_env": "", "default_model": "take-library"},
    "quality": {"provider_type": "compute", "provider": "ffprobe", "model_env": "", "default_model": "validation"},
}

PROVIDER_CATALOG: dict[str, list[str]] = {
    "text": ["ollama", "openai", "claude", "gemini", "deepseek", "mistral", "qwen", "llama"],
    "speech": ["piper", "elevenlabs"],
    "subtitle": ["local", "whisper", "openai"],
    "compute": ["ffmpeg", "minio", "ffprobe"],
}

EDITABLE_AGENTS = {
    "research",
    "hook",
    "script",
    "script_review",
    "emotion",
    "video_review",
    "storyboard",
    "scene",
    "publisher",
    "voice",
    "subtitle",
    "analytics",
    "thumbnail",
    "clip_research",
}


def default_model_for_agent(agent: str) -> dict[str, str]:
    meta = DEFAULT_AGENT_MODELS.get(agent)
    if not meta:
        return {"provider_type": "compute", "provider": "unknown", "model": "—"}
    model_env = meta.get("model_env", "")
    model = os.getenv(model_env, meta["default_model"]) if model_env else meta["default_model"]
    return {
        "provider_type": meta["provider_type"],
        "provider": meta["provider"],
        "model": model,
    }
