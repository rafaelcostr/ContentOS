# Model Manager (ContentOS V2.3)

Per-agent provider and model configuration stored in PostgreSQL (`agent_model_configs`).

## Defaults

| Agent | Type | Provider | Model |
|-------|------|----------|-------|
| research | text | ollama | qwen2.5:7b |
| script | text | ollama | qwen2.5:7b |
| scene | text | ollama | qwen2.5:7b |
| publisher | text | ollama | qwen2.5:7b |
| voice | speech | piper | pt_BR-faber-medium |
| subtitle | subtitle | local | large-v3 |

Compute agents (`editor`, `takes`, `quality`) are read-only in the dashboard.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/models` | List all agent configs |
| GET | `/api/v1/models/catalog` | Available providers per type |
| GET | `/api/v1/models/{agent}` | Single agent config |
| PUT | `/api/v1/models/{agent}` | Update provider + model |
| POST | `/api/v1/models/seed` | Insert missing defaults |

## Flow

```
Dashboard/API → PostgreSQL (agent_model_configs)
                      ↓
Celery worker → ModelManager (sync read + 30s cache) → build_*_provider()
                      ↓
AI Gateway → correct provider/model per agent
```

## Environment

Uses existing `DATABASE_URL`. Workers need `psycopg2` for sync DB reads (included in Docker images).

Fallback when DB unavailable: env vars (`OLLAMA_MODEL`, `PIPER_VOICE`, `WHISPER_MODEL`).

## Dashboard

`/models` — configure provider and model per agent without redeploy.
