# Smart Reuse Engine (ContentOS V4 — Epic 4)

Sugere reutilização de roteiros, hooks, CTAs e assets **antes** de gerar conteúdo novo — consulta a Knowledge Base (Epic 3).

## Fluxo

```
IntelligenceContext (topic + payload)
        ↓
   ReuseAdvisor
        ↓
   IKnowledgeQuery.search (por tipo: hook, script, cta, asset)
        ↓
   ReuseSuggestion[] (ordenado por similaridade)
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/reuse/suggest` | Sugestões de reuso para um tópico |

### Request

```json
{
  "project_id": "...",
  "topic": "GTA 6 segredos virais",
  "pipeline_id": "...",
  "payload": {
    "hook": { "selected_hook": "..." },
    "script": { "full_text": "..." }
  }
}
```

### Response

```json
[
  {
    "resource_type": "hook",
    "resource_id": "...",
    "title": "Hook: ...",
    "similarity": 0.82,
    "reason": "Alta similaridade — considere reutilizar em vez de gerar novo conteúdo",
    "metadata": { "snippet": "..." }
  }
]
```

## Configuração

| Env | Default | Descrição |
|-----|---------|-----------|
| `REUSE_MIN_SIMILARITY` | `0.35` | Limiar mínimo |
| `REUSE_MAX_PER_TYPE` | `3` | Máx. por tipo de recurso |
| `REUSE_MAX_TOTAL` | `10` | Máx. total |
| `REUSE_CACHE_TTL` | `30` | Cache em segundos (meta &lt;500ms) |

## DI Registry

`DbReuseAdvisor` registrado no startup do gateway junto com `DbKnowledgeQuery`.

Usado internamente por `ContentIntelligenceService` → `reuse_suggestions` no payload futuro (`content_intelligence` step).

## Pré-requisito

Indexar pipelines na Knowledge Base:

```http
POST /api/v1/knowledge/index/{pipeline_id}
```

Sem entradas indexadas, sugestões retornam lista vazia (não falha).

## Roadmap

- V4.0.5: step `content_intelligence` inclui `reuse_suggestions` automaticamente
- Epic 7: Learning invalida cache após novos indexados
