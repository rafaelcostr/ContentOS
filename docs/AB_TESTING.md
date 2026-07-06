# A/B Testing — Epic 6 (V4.1.1)

Automatic variant generation and winner selection inside the `content_intelligence` step.

## Overview

For each pipeline run (template `v4-intelligence`), after viral analysis the system generates **3 variants** per dimension:

| Dimension | Source | Winner applied to |
|-----------|--------|-------------------|
| `hook` | `hook_text`, alternatives | `selected_hook`, `hook_text` |
| `title` | `script.title` | `script.title` |
| `cta` | `script.call_to_action` | `script.call_to_action` |
| `thumbnail` | text concepts | `thumbnail_concept` → thumbnail agent |
| `opener` | hook / script intro | `opener_text` |

Winners are scored with viral sub-signals (no extra LLM). All variants are persisted in `ab_variants`.

## Architecture

```
content_intelligence
├── reuse_advisor
├── viral_engine
└── ab_testing (Epic 6)
    ├── generators.py   — 3 variants per dimension
    ├── scoring.py      — viral-weighted scores
    └── service.py      — select winner + merge payload
```

## Payload output

```json
{
  "viral_report": { "...": "..." },
  "reuse_suggestions": [],
  "ab_test": {
    "dimensions": [
      {
        "dimension": "hook",
        "variants": [{ "variant_id": "...", "value": "...", "score": 82.5 }],
        "winner_index": 0,
        "winner": { "variant_id": "...", "value": "...", "score": 82.5 }
      }
    ],
    "winners": { "hook": { "...": "..." } }
  },
  "hook_text": "<winner>",
  "thumbnail_concept": "<winner concept>"
}
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/ab-variants/generate` | Generate + optional persist |
| `GET` | `/api/v1/ab-variants/pipeline/{pipeline_id}` | List persisted sets |

### Generate example

```bash
curl -X POST /api/v1/ab-variants/generate \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "project_id": "...",
    "pipeline_id": "...",
    "topic": "GTA 6",
    "payload": { "hook_text": "Ninguém esperava isso" },
    "persist": true
  }'
```

## Events

- `ab.variant.selected` — emitted per dimension when a winner is chosen (alias `AbVariantSelected`)

## Database

Table `ab_variants`:

- `pipeline_id`, `dimension`, `variants` (JSON), `winner_index`, `winner`
- Migration: `012_v4_ab_variants.py`

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `AB_TESTING_ENABLED` | `true` | Run A/B inside `content_intelligence` |
| `AB_VARIANTS_PER_DIMENSION` | `3` | Variants per dimension (2–5) |

## Dashboard

`/ab-testing` — manual generate + view winners by pipeline.

## Tests

```bash
pytest tests/test_ab_testing.py -q
```
