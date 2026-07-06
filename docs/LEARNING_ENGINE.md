# Learning Engine — Epic 7 (V4.2.3)

Fecha o loop pós-pipeline: extrai sinais internos (hook, CTA, specialist, prompts, scores) e persiste em **Memory** + **Knowledge Base**.

## Limitação

Sem métricas externas de plataforma (views TikTok, etc.), o learning é **interno** — baseado em `content_score`, `viral_report`, variantes A/B e payload do pipeline. Integração OAuth analytics = fase futura.

## Componentes

| Classe | Path | Função |
|--------|------|--------|
| `LearningEngine` | `application/learning/service.py` | Orquestra extract → memory → KB → persist |
| `extractor` | `application/learning/extractor.py` | Sinais do payload |
| `memory_applier` | `application/learning/memory_applier.py` | Atualiza `ProjectMemory` |
| `LearningRepository` | `infrastructure/learning_repository.py` | Tabela `learning_insights` |

## Disparo

Agente **async** `learning` — enfileirado automaticamente ao completar pipelines V4 com `enable_learning: true` (templates `v4-intelligence`, `v4-multi-text`, `v4-multi-full`).

```
pipeline.completed → dispatch_async_agent("learning")
```

## Sinais extraídos

| Tipo | Fonte |
|------|-------|
| `hook` | A/B winner, `selected_hook`, `script.hook` |
| `cta` | `script.call_to_action` |
| `specialist` | `specialist_selection` |
| `content_score` | `content_score_report` |
| `viral_score` | `viral_report` |
| `prompt` | `prompts_used`, `specialist_prompt_pack` |

## Memory (auto-apply)

Quando `content_score ≥ 55` ou `viral_score ≥ 6.5`:

- `hook_patterns` — hook promovido
- `cta` — CTA do pipeline
- `niche` / `goal` — do specialist (se vazio)
- `history` — entrada resumida

## Knowledge Base

Indexa entradas `hook`, `cta`, `prompt` derivadas do learning (texto; embeddings opcionais depois).

## API

| Method | Path |
|--------|------|
| `POST` | `/api/v1/learning/record` |
| `GET` | `/api/v1/learning/pipeline/{pipeline_id}` |
| `GET` | `/api/v1/learning/insights?project_id=` |

## Environment

| Variable | Default |
|----------|---------|
| `LEARNING_ENGINE_ENABLED` | `true` |
| `LEARNING_AUTO_APPLY_MEMORY` | `true` |
| `LEARNING_AUTO_INDEX_KB` | `true` |
| `LEARNING_MIN_CONTENT_SCORE` | `55` |
| `LEARNING_MIN_VIRAL_SCORE` | `6.5` |

## Evento

`learning.recorded`

## Dashboard

`/learning` — insights por projeto.

## Tests

```bash
pytest tests/test_learning_engine.py -q
```

## Migration

`015_v4_learning_engine.py` — tabela `learning_insights`
