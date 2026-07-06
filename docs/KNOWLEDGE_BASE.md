# Knowledge Base (ContentOS V4 — Epic 3)

Memória permanente semântica — roteiros, hooks, vídeos, analytics indexados com embeddings via AI Gateway.

## Componentes

| Classe | Pacote | Função |
|--------|--------|--------|
| `KnowledgeBaseService` | `application/knowledge_base.py` | Fachada search + history + index |
| `EmbeddingIndex` | `application/embedding_index.py` | Vetoriza e persiste entradas |
| `SemanticSearch` | `application/semantic_search.py` | Cosine similarity + fallback texto |
| `ContentHistory` | `application/content_history.py` | Histórico cronológico |
| `VersionHistory` | `application/version_history.py` | Revisões por resource |
| `KnowledgeIndexer` | `application/knowledge_indexer.py` | Indexa pipeline completo |
| `GatewayEmbeddingClient` | `infrastructure/embedding_client.py` | AI Gateway `/v1/embeddings` |

## Tabela `knowledge_entries`

Migration `011_v4_knowledge_base`. Embeddings em JSON (sem pgvector — cosine em Python).

## Resource types

`script`, `hook`, `video`, `asset`, `analytics`, `title`, `cta`, `prompt`

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/knowledge/search` | Busca semântica |
| GET | `/api/v1/knowledge/history/{project_id}` | Histórico indexado |
| GET | `/api/v1/knowledge/versions/{type}/{id}?project_id=` | Versões de um recurso |
| POST | `/api/v1/knowledge/index/{pipeline_id}` | Reindexar pipeline |

### Search example

```json
POST /api/v1/knowledge/search
{
  "project_id": "...",
  "query": "hook viral sobre GTA",
  "resource_types": ["hook", "script"],
  "limit": 10,
  "min_similarity": 0.3
}
```

## Variáveis de ambiente

| Var | Default | Descrição |
|-----|---------|-----------|
| `AI_GATEWAY_URL` | `http://ai-gateway:8020` | Gateway de embeddings |
| `KNOWLEDGE_EMBED_PROVIDER` | `ollama` | Provider |
| `KNOWLEDGE_EMBED_MODEL` | — | Modelo opcional |
| `KNOWLEDGE_EMBED_DISABLED` | — | `true` = fallback texto apenas |

## DI Registry

No startup do gateway, `DbKnowledgeQuery` registra `IKnowledgeQuery` real — preparado para Epic 4 Smart Reuse.

## Migration

```bash
cd packages/database && alembic upgrade head
```
