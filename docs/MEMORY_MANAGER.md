# Memory Manager (ContentOS V2.4)

Per-project creative memory injected into prompts as `{{memory_context}}`.

## Fields

| Field | Type | Example |
|-------|------|---------|
| tone | string | casual e direto |
| vocabulary | list | hype, viral, insano |
| cta | string | Siga para mais |
| avg_duration | float | 45 |
| hook_style | string | pergunta nos 3s |
| niche | string | games |
| goal | string | viralizar no TikTok |
| style | json | `{"visual": "neon"}` |
| history | json | `[{"summary": "..."}]` |

### Project DNA (V4 Epic 8)

| Field | Type | Example |
|-------|------|---------|
| humor_level | float 0–1 | 0.7 |
| pace | slow \| medium \| fast | fast |
| visual_style | json | `{"primary_color": "#FF0050"}` |
| narrator_persona | string | hype gamer |
| preferred_formats | list | tiktok, youtube_shorts |
| hook_patterns | list | pergunta chocante |
| cta_style | string | urgente |

See [PROJECT_DNA.md](./PROJECT_DNA.md).

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects/{id}/memory` | Get memory + preview |
| PUT | `/api/v1/projects/{id}/memory` | Update memory |
| GET | `/api/v1/projects/{id}/dna` | Get DNA only |
| PATCH | `/api/v1/projects/{id}/dna` | Partial DNA update |

New projects get an empty memory row on creation.

## Injection

`BaseAgentHandler.render_prompt(..., project_id=...)` auto-fills:

- `memory_context` — formatted string for prompts
- `dna_context` — DNA-only block (V4)
- `niche` — if not already in variables
- `narrator_persona`, `pace`, `cta_style` — DNA fields (V4)

## Example context output

```
Nicho: games. Tom: casual e direto. Estilo de gancho: pergunta chocante. Objetivo: viralizar no TikTok. CTA padrão: Siga para mais. Duração alvo: 45s.
```

## Dashboard

`/memory` — select project, edit fields, preview `memory_context`.

Workers cache memory for 30s (sync DB read via psycopg2).
