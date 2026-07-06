# AI Gateway (ContentOS V2.1 + Fases 9–10)

Serviço HTTP central para todas as operações de IA. Agentes **nunca** chamam Ollama/Piper/Whisper diretamente quando `USE_AI_GATEWAY=true` (padrão).

## Architecture

```
Agent Handler
  → build_*_provider(agent=step) / Gateway*Provider
  → ai-client (HTTP)
  → AI Gateway (:8020)
  → RoutingService (Model Manager por agente)
  → ProviderRegistry
  → adapters (ai-core)
  → Ollama / Piper / Whisper / Cloud
         ↓ (se gateway falhar e AI_GATEWAY_FALLBACK=true)
    adapters diretos locais (sem recursão)
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health |
| GET | `/v1/providers` | List provider keys (text, speech, subtitle, image, vision, embedding) |
| GET | `/v1/providers/resolve` | Resolve route (`agent`, `provider_type`) |
| POST | `/v1/text/chat-json` | JSON chat (`agent` → Model Manager) |
| POST | `/v1/speech/tts` | TTS → `audio/mpeg` |
| POST | `/v1/subtitle/transcribe` | Transcription (multipart) |
| POST | `/v1/image/generate` | Image → `image/jpeg` |
| POST | `/v1/vision/analyze` | Vision (multipart) |
| POST | `/v1/embeddings` | Embeddings |

API Gateway proxy: `GET /api/v1/providers/ai-gateway/health`

## Environment

```env
USE_AI_GATEWAY=true
AI_GATEWAY_URL=http://ai-gateway:8020
AI_GATEWAY_FALLBACK=true

TEXT_PROVIDER=ollama
SPEECH_PROVIDER=piper
SUBTITLE_PROVIDER=local
IMAGE_PROVIDER=local
VISION_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama

OLLAMA_VISION_MODEL=llava
OLLAMA_EMBED_MODEL=nomic-embed-text
```

## Routing por agente

```powershell
curl "http://localhost:8020/v1/providers/resolve?agent=script&provider_type=text"
curl "http://localhost:8020/v1/providers/resolve?agent=thumbnail&provider_type=image"
```

Prioridade: **Model Manager (DB)** → defaults por agente → request explícito.

## Packages

| Package | Role |
|---------|------|
| `packages/ai-core` | Protocols, `ProviderRegistry`, `RoutingService`, `AIService`, adapters |
| `packages/ai-client` | HTTP client + `Gateway*Provider` |
| `services/ai-gateway` | FastAPI :8020 |

## Providers

| Type | Keys |
|------|------|
| text | ollama, openai, claude, gemini, deepseek, mistral, qwen, llama |
| speech | piper, elevenlabs |
| subtitle | local, whisper, openai |
| image | local, pillow |
| vision | ollama, llava |
| embedding | ollama |

## V1 compatibility

- Pipeline 9 steps continua disponível (`v1-default`)
- `USE_AI_GATEWAY=false` força adapters diretos (emergência)
- Fallback não reentra no gateway (evita loop)

## Tests

```powershell
pytest tests/test_ai_gateway.py tests/test_ai_gateway_routing.py tests/test_advanced_providers.py -v
```
