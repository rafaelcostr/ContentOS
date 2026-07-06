# ContentOS

SaaS profissional de criação automatizada de vídeos curtos para TikTok, YouTube Shorts e Instagram Reels.

Recebe um **tema** (ex.: `GTA 6`) e executa um pipeline de agentes de IA — pesquisa, roteiro, mídia, narração, legendas, edição, qualidade e publicação (dry-run por padrão).

## Documentação

### ContentOS V3 (auditoria)

| Doc | Descrição |
|-----|-----------|
| [PRD](./docs/PRD.md) | Requisitos de produto V3 |
| [Gap Analysis](./docs/GAP_ANALYSIS.md) | EXISTS / PARTIAL / MISSING |
| [Roadmap](./docs/ROADMAP.md) | Evolução priorizada (Tiers A–E) |
| [ADR](./docs/ADR.md) | Decisões arquiteturais |
| [RBAC](./docs/RBAC.md) | Papéis viewer / editor / admin |

### Referência

| Doc | Descrição |
|-----|-----------|
| [Arquitetura](./docs/ARCHITECTURE.md) | Visão geral, diagramas, decisões |
| [Fluxo](./docs/FLOW.md) | Pipeline V1/V2, sequência, retry |
| [API](./docs/API.md) | Endpoints principais |
| [Naming](./docs/NAMING.md) | Nomes da missão vs código |
| [Fases](./docs/PHASES.md) | Histórico Fases 1–12 (V1/V2) |
| [Providers](./docs/PROVIDERS.md) | Como trocar IA sem alterar agentes |
| [Plugins](./docs/PLUGINS.md) | Sistema de extensibilidade |
| [Stack Local](./docs/LOCAL_STACK.md) | Ollama + Piper + Whisper |
| [Editor](./docs/EDITOR.md) | FFmpeg timeline, efeitos, quality |
| [Observabilidade](./docs/OBSERVABILITY.md) | CPU, GPU, agents, analytics |
| [CI/CD](./docs/CI_CD.md) | GitHub Actions, testes, Playwright |
| [Kubernetes](./docs/K8S.md) | Deploy produção + HPA |
| [Agentes](./docs/AGENTS.md) | Especificação dos agentes |

### V2 (extensões)

| Doc | Descrição |
|-----|-----------|
| [Arquitetura V2](./docs/ARCHITECTURE_V2.md) | Componentes V2 e pipeline 14 steps |
| [Migração V1→V2](./docs/V2_MIGRATION.md) | Guia de upgrade |
| [AI Gateway](./docs/AI_GATEWAY.md) | Roteamento central de IA |
| [Event Bus](./docs/EVENT_BUS.md) | Redis Streams + event store |
| [Analytics AI](./docs/ANALYTICS_AI.md) | Insights pós-pipeline |
| [Plugin Marketplace](./docs/PLUGIN_MARKETPLACE.md) | Plugins instaláveis |
| [Content Sources](./docs/CONTENT_SOURCES.md) | Clip research + assets |
| [Asset Manager V2](./docs/ASSET_MANAGER_V2.md) | Dedup, tags, indexação |
| [Guias de extensão](./docs/guides/) | ADD_PROVIDER, ADD_AGENT, ADD_PLUGIN, ADD_SOURCE |

## Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.13, FastAPI, Celery, SQLAlchemy |
| Frontend | Next.js 15, React, Tailwind, Shadcn UI |
| Dados | PostgreSQL, Redis, MinIO |
| IA (local) | Ollama + Qwen2.5/3, Piper TTS, Whisper large-v3 |
| Mídia | FFmpeg |

## Início Rápido

```powershell
copy .env.example .env
docker compose -f docker/docker-compose.yml up -d --build
python scripts/wait_for_services.py
```

| Serviço | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API Gateway | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| AI Gateway | http://localhost:8020/docs |
| MinIO Console | http://localhost:9001 |
| Ollama | http://localhost:11434 |
| Piper | http://localhost:5000/health |
| Whisper | http://localhost:8080/health |
| Flower | http://localhost:5555 |

## Fase Atual

**Fases 8–12** ✅ — Asset pipeline E2E, AI Gateway unificado, providers avançados, dashboard completo, documentação.

```powershell
# Testes locais
pip install -r requirements-dev.txt
pytest tests/ -v -m "not integration" --ignore=tests/test_api_integration.py

# Migrations (DB existente)
cd packages/database
alembic upgrade head

# E2E V1
python scripts/e2e_pipeline.py

# E2E V2 dynamic (14 steps)
$env:E2E_WORKFLOW = "v2-dynamic"
python scripts/e2e_pipeline.py
```

## Pipeline

**V1 (`v1-default`)** — 9 steps:

```
research → script → scene → takes → voice → subtitle → editor → quality → publisher
```

**V2 (`v2-dynamic`)** — 14 steps:

```
research → script → scene → clip_research → asset_collector → asset_index →
takes → voice → subtitle → editor → quality → publisher → thumbnail → analytics
```

No dashboard: **Projetos** → criar pipeline → workflow **V2 Dynamic**.

## Estrutura

```
apps/backend/              → API Gateway
apps/dashboard/            → Next.js 15
services/workflow-engine/  → Orquestrador
services/agents-worker/    → Agentes Celery (V1 + V2)
services/ai-gateway/       → Roteamento central de IA
packages/ai-core/          → ProviderRegistry, adapters
packages/ai-client/        → Client HTTP dos agentes
packages/prompts/          → Prompt Manager
packages/models/           → Model Manager
packages/memory/           → Memory Manager
packages/cache/            → Cache Manager
packages/cost/             → Cost Manager
packages/events/           → Event Bus
packages/content-sources/  → Content Sources
packages/storage/          → Asset Manager V2
packages/shared/           → Contratos, base handlers (compat V1)
packages/database/         → Models + Alembic
```

## Providers (DI)

```env
USE_AI_GATEWAY=true        # padrão — agentes nunca chamam Ollama direto
TEXT_PROVIDER=ollama
SPEECH_PROVIDER=piper
SUBTITLE_PROVIDER=local
IMAGE_PROVIDER=local
VISION_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
```

Agentes usam `ProviderFactory` / `Gateway*Provider` → **AI Gateway** → adapters em `ai-core`.

Modelos por agente: dashboard **Modelos** ou tabela `agent_model_configs`.

## Dashboard (rotas principais)

| Rota | Função |
|------|--------|
| `/` | Painel |
| `/jobs` | Produção em tempo real (Parar / Excluir) |
| `/workflow` | Orquestração V1/V2 |
| `/assets` | Biblioteca indexada |
| `/ai-gateway` | Health + providers |
| `/models` | Modelo por agente |
| `/prompts` | Prompt Manager |
| `/memory` | Memória do projeto |
| `/content-sources` | Fontes de mídia |
| `/events` | Event Bus |
| `/costs` | Custos |

## Testes

```powershell
pip install -r requirements-dev.txt

# Unitários
pytest tests/ -v -m "not integration" --ignore=tests/test_api_integration.py

# Integração API (Postgres required)
pytest tests/test_api_integration.py -v

# Playwright E2E
cd apps/dashboard && npm run test:e2e
```

## Licença

Proprietário.
