# SEO Engine — V5.2.3

Otimização de **títulos, hashtags e descrições** para publicação em vídeos curtos.

## O que gera

| Campo | Descrição |
|-------|-----------|
| `title` | Título principal (CTR) |
| `title_variants[]` | Até 3 alternativas A/B |
| `description` | Descrição até 500 chars |
| `hashtags[]` | 5–10 tags sem `#` |
| `keywords[]` | Termos de busca |
| `platforms` | Cópia por TikTok / Shorts / Reels |
| `seo_score` | 0–100 |

## Sinais usados

| Sinal | Fonte no payload |
|-------|------------------|
| Roteiro | `script` (hook, body, CTA) |
| Hook selecionado | `selected_hook` |
| DNA da marca | `project_dna.brand_keywords` |
| Tendências | `trend_intelligence` |

## Pipeline

Step `seo` — no `factory-full`, após `analytics` e antes de `publisher`; no `v5-media-autopilot`, após `ai_director` e `creative_memory`, antes de `publisher`:

- `factory-full` (31 steps)
- `v5-media-autopilot` (18 steps)

O step `publisher` consome `seo_package` quando presente (sem chamar LLM de metadados).

## API

```
POST /api/v1/seo/optimize
```

```json
{
  "project_id": "...",
  "topic": "GTA 6",
  "payload": { "script": {}, "project_dna": {} }
}
```

## Agent

`SeoAgentHandler` — `services/agents-worker/handlers/seo.py`

Polish opcional via LLM (`SEO_USE_LLM=true`, prompt `seo.md`).

## Content Score

`extract_seo()` prioriza `seo_package.seo_score` quando presente.

## Dashboard

`/seo` — preview de metadados por plataforma.

## Variáveis de ambiente

| Variável | Default | Descrição |
|----------|---------|-----------|
| `SEO_ENGINE_ENABLED` | `true` | Liga o step `seo` |
| `SEO_USE_LLM` | `true` | Polish LLM opcional |

## Testes

```bash
pytest tests/test_seo_engine.py -q
```

