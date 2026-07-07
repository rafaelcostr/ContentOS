# Creative Memory — V5.2.5

Camada unificada que **mescla Learning Engine + Knowledge Base** em um único contexto criativo.

## O que faz

1. Consome ou executa `LearningEngine` (hooks, CTAs, scores → `project_memory`)
2. Indexa/busca na KB semântica por tema
3. Emite `creative_memory_context` injetado em `{{memory_context}}` dos prompts

## Saída (`creative_memory`)

| Campo | Descrição |
|-------|-----------|
| `learning_report` | Relatório do Learning Engine |
| `knowledge_hits[]` | Trechos relevantes da KB |
| `creative_memory_context` | Texto para prompts |
| `creative_memory_hints` | `hook_hint`, `cta_hint`, `kb_hit_count` |
| `memory_applied` | Se memória do projeto foi atualizada |

## Pipeline

Step `creative_memory`:

- `factory-full` — após `knowledge_base`, antes de `analytics` (31 steps)
- `v5-media-autopilot` — após `seo`, antes de `publisher` (18 steps)

Steps `learning` e `knowledge_base` permanecem nos pipelines V4/factory; `creative_memory` consolida o resultado.

## API

```
POST /api/v1/creative-memory/merge
```

## Agent

`CreativeMemoryAgentHandler` — `handlers/creative_memory.py`

## Dashboard

`/creative-memory`

## Variáveis de ambiente

| Variável | Default | Descrição |
|----------|---------|-----------|
| `CREATIVE_MEMORY_ENABLED` | `true` | Liga o step |
| `CREATIVE_MEMORY_KB_SEARCH_LIMIT` | `5` | Hits semânticos por merge |

## Testes

```bash
pytest tests/test_creative_memory.py -q
```
