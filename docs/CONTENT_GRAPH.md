# Content Relation Graph — Epic 11 (V4.3.1)

Grafo de relacionamentos entre vídeos, roteiros, assets, specialists, prompts, KB e learning insights.

## Nós

| Tipo | Fonte |
|------|-------|
| `pipeline` | `pipelines` |
| `video` | `videos` |
| `script` | `scripts` |
| `asset` | `assets` (render, thumb, script) |
| `specialist` | `content_intelligence` / learning |
| `prompt` | `prompts_used` nos jobs |
| `knowledge_entry` | `knowledge_entries` |
| `learning_insight` | `learning_insights` |

## Arestas

| Relação | Exemplo |
|---------|---------|
| `produces` | pipeline → script/video |
| `derived_from` | video → script |
| `uses` | video/script → asset |
| `selected` | pipeline → specialist |
| `references` | pipeline → prompt |
| `indexed_from` | knowledge_entry → pipeline |
| `learned_from` | learning_insight → pipeline |

## População automática

- **Learning Engine** — após `learning.recorded` (`CONTENT_GRAPH_AUTO_BUILD=true`)
- **Knowledge index** — `POST /knowledge/index/{pipeline_id}` rebuilda o grafo
- **Manual** — `POST /graph/build/{pipeline_id}`

## API

| Method | Path |
|--------|------|
| `POST` | `/api/v1/graph/build/{pipeline_id}` |
| `GET` | `/api/v1/graph/project/{project_id}` |
| `GET` | `/api/v1/graph/neighbors?project_id=&node_type=&node_id=` |

## Environment

| Variable | Default |
|----------|---------|
| `CONTENT_GRAPH_ENABLED` | `true` |
| `CONTENT_GRAPH_AUTO_BUILD` | `true` |

## Evento

`graph.updated`

## Dashboard

`/content-graph`

## Tests

```bash
pytest tests/test_content_graph.py -q
```

## Migration

`017_v4_content_graph.py` — tabela `content_relations`
