# Cost Manager (ContentOS V2.6 / Tier A4)

Tracks AI usage and estimated cost per operation — even local providers register **$0** entries with duration and units.

## Metrics per entry

| Field | Description |
|-------|-------------|
| `operation` | `text_chat`, `speech_tts`, `subtitle_stt`, `image_generate` |
| tokens_input / tokens_output | Units depend on operation (see below) |
| duration_ms | Call duration |
| provider / model | From Model Manager or provider instance |
| estimated_cost_usd | Pricing table (0 for local) |
| from_cache | True when served from Redis cache (text only) |

### Units by operation

| Operation | tokens_input | tokens_output |
|-----------|--------------|---------------|
| `text_chat` | estimated prompt tokens | estimated response tokens |
| `speech_tts` | character count | audio bytes / 100 |
| `subtitle_stt` | audio minutes × 100 | segment count |
| `image_generate` | 0 | image count |

## Storage

PostgreSQL table `cost_entries`, linked to `project_id`, `pipeline_id`, `job_id`.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/costs/overview` | Totals for user's projects |
| GET | `/api/v1/costs/projects/{id}` | Per-project breakdown |
| GET | `/api/v1/costs/pipelines/{id}` | Per-pipeline + recent entries |

## Pricing

Local providers (`ollama`, `piper`, `whisper`, `local`, `ffmpeg`, …) → **$0.00**

Cloud estimates (approximate):

| Modality | Provider examples |
|----------|-------------------|
| Text | OpenAI, Claude, Gemini, DeepSeek, Mistral |
| Speech | ElevenLabs (per 1K chars), OpenAI TTS |
| Subtitle | OpenAI Whisper (per minute) |
| Image | OpenAI (per image) |

## Integration

| Agent | Recording |
|-------|-----------|
| research, script, scene, … | `chat_json_with_cache` → `record_text_chat` |
| voice | `record_speech` |
| subtitle | `record_subtitle` |
| thumbnail | `record_image` |

Helpers on `BaseAgentHandler`: `_record_speech_cost`, `_record_subtitle_cost`, `_record_image_cost`.

## Dashboard

`/costs` — overview, breakdown by provider/agent.
