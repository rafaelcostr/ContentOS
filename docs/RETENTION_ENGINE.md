# Retention Engine — V5.2.1

Análise **segundo a segundo** da retenção prevista antes de publicar.

## O que analisa

Sem vision frame-a-frame (fora de escopo V5). Usa metadados da timeline:

| Sinal | Fonte no payload |
|-------|------------------|
| Cenas | `scenes[]` start/end |
| Movimento | `director_plan.segments[]` |
| Emoção / hook | `emotion`, `viral_report` |
| Legendas | `segments[]` (SRT timing) |
| Duração | `duration_seconds`, render probe |

## Saída (`retention_report`)

| Campo | Descrição |
|-------|-----------|
| `overall_score` | 0–100 |
| `timeline[]` | `{ second, retention_pct, scene_label }` |
| `drop_seconds` | segundos com queda ≥ 4% |
| `weak_segments` | cenas com retenção baixa |
| `recommendations` | ações sugeridas |

## Pipeline

Step `retention` — **após `quality`** (pós-render), antes de `video_review`:

- `factory-full`: `editor → thumbnail → quality → retention → video_review`
- `v5-media-autopilot`: `editor → quality → retention`

Modos em `retention_report.analysis_mode`:

| Modo | Quando |
|------|--------|
| `post_render` | `quality_passed` / `quality_score` presentes no payload |
| `post_render_partial` | `render_ref` ou `render_diagnostics` sem quality |
| `pre_render` | Apenas metadados de roteiro (preview API) |

Penalidades pós-render: falha de quality, clips placeholder, áudio silencioso.

## API

```
POST /api/v1/retention/analyze
```

```json
{
  "project_id": "...",
  "topic": "GTA 6",
  "payload": { "scenes": [], "director_plan": {}, "emotion": {} }
}
```

## Agent

`RetentionAgentHandler` — `services/agents-worker/handlers/retention.py`

## Content Score

`extract_retention()` prioriza `retention_report.overall_score` quando presente.

## Dashboard

`/retention` — curva visual + segmentos fracos.

## Testes

```bash
pytest tests/test_retention_engine.py tests/test_retention_retry.py -q
```

## V5.2.2 — Retention → auto_retry

Quando a retenção prevista fica abaixo dos limiares, o pipeline pode **rebobinar** de forma direcionada:

| Fraqueza detectada | `retention_retry_target` | `creative_retry_from` |
|--------------------|--------------------------|------------------------|
| Hook fraco (0–5s) | `hook` | `hook` |
| Take/corpo estático | `take` | `takes` |
| CTA / completion baixo | `cta` | `script` |

### Variáveis de ambiente

| Variável | Default | Descrição |
|----------|---------|-----------|
| `RETENTION_RETRY_ENABLED` | `true` | Liga retry dirigido por retenção |
| `RETENTION_MIN_SCORE` | `65` | Score geral mínimo |
| `RETENTION_MIN_HOOK_PCT` | `70` | Retenção no hook (3s) |
| `RETENTION_MIN_COMPLETION_PCT` | `40` | Completion mínimo |

### Fluxo

1. Step `retention` emite `retention_passed`, `retention_retry_plan`, `creative_retry_from`.
2. Pipelines **sem** `auto_retry` (ex. `v5-media-autopilot`): retry imediato após `retention` se falhou.
3. Pipelines **com** `auto_retry` (ex. `factory-full`): `auto_retry` combina `video_review_passed` + `retention_passed` e o engine rebobina.

`RetentionRetryPlanner` — `packages/intelligence/.../retention/retry_policy.py`

