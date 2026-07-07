# ContentOS V2 — Guia de Migração

Este guia cobre a migração de uma instalação **V1** (9 agentes síncronos) para **V2** (AI Gateway, Event Bus, plugins, content sources, analytics, etc.) **sem quebrar** o pipeline principal.

## Princípio

O pipeline V1 de 9 steps (`research` → `publisher`) permanece intacto. Os recursos V2 são **aditivos** e controlados por variáveis de ambiente ou por **workflow templates**.

---

## Checklist rápido

| Passo | Ação |
|-------|------|
| 1 | Atualizar código / imagens Docker |
| 2 | Copiar novas variáveis do `.env.example` |
| 3 | Subir `ai-gateway` (Compose ou K8s) |
| 4 | Reiniciar gateway + workflow-engine (seed de templates) |
| 5 | Validar health endpoints |
| 6 | (Opcional) Usar workflow `v2-full` |

---

## 1. Variáveis de ambiente novas

Adicione ao `.env` (valores seguros para começar):

```env
# AI Gateway
USE_AI_GATEWAY=true
AI_GATEWAY_URL=http://ai-gateway:8020

# Workflow template padrão
DEFAULT_WORKFLOW=v1-default

# Event Bus
EVENT_STREAM_KEY=contentos:stream:events

# V2 async (desligados por padrão — compatível com V1)
ENABLE_ANALYTICS_AI=true
ENABLE_THUMBNAIL=false
ENABLE_V2_CLIP_PIPELINE=false

# Content Sources
CONTENT_SOURCES_ENABLED=local_library,own_library

# Plugins
PLUGINS_ROOT=/app/plugins
```

### Comportamento por flag

| Variável | Default | Efeito |
|----------|---------|--------|
| `USE_AI_GATEWAY` | `true` | Agentes roteiam IA via AI Gateway |
| `DEFAULT_WORKFLOW` | `v1-default` | Template usado ao criar pipeline sem `workflow_name` |
| `ENABLE_V2_CLIP_PIPELINE` | `false` | Dispara `clip_research` após step `scene` |
| `ENABLE_THUMBNAIL` | `false` | Dispara agente thumbnail ao completar pipeline |
| `ENABLE_ANALYTICS_AI` | `true` | Dispara analytics AI ao completar pipeline |

---

## 2. Workflow templates

Dois templates built-in são inseridos automaticamente na tabela `workflows` no startup:

| Nome | Steps | V2 async |
|------|-------|----------|
| `v1-default` | 9 steps V1 | Controlado só por env |
| `v2-full` | 9 steps V1 | Clip + thumbnail + analytics via `config` (async) |
| `v2-dynamic` | 16 steps V2 | Pipeline completo síncrono com media_analyze |

### API

```http
GET /api/v1/workflows
GET /api/v1/workflows/v2-full
```

### Criar pipeline com template

```http
POST /api/v1/projects/{id}/pipelines
{
  "topic": "Como funciona IA",
  "workflow_name": "v2-full"
}
```

O campo `workflow_name` é opcional; se omitido, usa `DEFAULT_WORKFLOW`.

---

## 3. Docker Compose

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Serviços V2 relevantes: `ai-gateway`, `gateway`, `workflow-engine`, `agents-worker`.

---

## 4. Kubernetes

O manifest `k8s/base/ai-gateway.yaml` foi adicionado. O ConfigMap inclui variáveis V2.

```bash
kubectl apply -k k8s/base/
kubectl -n contentos get pods
```

Build da imagem:

```bash
docker build -f docker/Dockerfile.ai-gateway -t your-registry/contentos/ai-gateway:v2 .
```

---

## 5. Banco de dados

Novas tabelas V2 (criadas via `create_tables` no startup):

- `agent_model_configs`, `project_memory`, `cost_entries`
- `domain_events`, `analytics_insights`
- `installed_plugins`, `pipeline_asset_collections`
- `workflows` (templates)
- Campo `workflow_name` em `pipelines`
- Campos `sha256`, `tags`, `version` em `assets`

**Instalações existentes:** execute migrations Alembic:

```bash
cd packages/database
alembic upgrade head
```

Ou em dev/local, recriar o volume Postgres é o caminho mais simples.

---

## 6. Rollback

Para voltar ao comportamento V1 puro:

```env
DEFAULT_WORKFLOW=v1-default
USE_AI_GATEWAY=false
ENABLE_V2_CLIP_PIPELINE=false
ENABLE_THUMBNAIL=false
ENABLE_ANALYTICS_AI=false
```

Nenhum step do pipeline principal precisa ser removido.

---

## 7. Documentação V2

| Doc | Conteúdo |
|-----|----------|
| [ARCHITECTURE_V2.md](./ARCHITECTURE_V2.md) | Visão completa V2 |
| [AI_GATEWAY.md](./AI_GATEWAY.md) | Roteamento de IA |
| [EVENT_BUS.md](./EVENT_BUS.md) | Redis Streams + event store |
| [ANALYTICS_AI.md](./ANALYTICS_AI.md) | Insights pós-pipeline |
| [PLUGIN_MARKETPLACE.md](./PLUGIN_MARKETPLACE.md) | Plugins dinâmicos |
| [CONTENT_SOURCES.md](./CONTENT_SOURCES.md) | Fontes + clip research |
| [ASSET_MANAGER_V2.md](./ASSET_MANAGER_V2.md) | Dedup, tags, search |
| [guides/](./guides/) | ADD_PROVIDER, ADD_CONTENT_SOURCE, ADD_PLUGIN, ADD_AGENT |

---

## 8. Validação pós-migração

```powershell
# Health
curl http://localhost:8000/health
curl http://localhost:8020/health

# Templates
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/workflows

# Testes
pytest tests/test_workflow_templates.py tests/test_event_bus.py -v
```

Pipeline E2E:

```powershell
python scripts/e2e_pipeline.py
```

