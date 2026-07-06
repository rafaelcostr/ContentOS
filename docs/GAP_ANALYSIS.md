# ContentOS V3 — Gap Analysis

| Campo | Valor |
|-------|--------|
| **Data da auditoria** | 2026-07-03 |
| **Escopo** | Monorepo completo (apps, services, packages, docker, k8s, docs) |
| **Regra** | Não reescrever o que está EXISTS; evoluir PARTIAL; criar só MISSING |

**Legenda**

| Status | Significado |
|--------|-------------|
| **EXISTS** | Implementado e utilizável no fluxo atual |
| **PARTIAL** | Existe base, falta cobertura, naming ou profundidade V3 |
| **MISSING** | Não existe no código |

---

## 1. Estrutura do monorepo

### Apps
| Path | Função |
|------|--------|
| `apps/backend` | API Gateway FastAPI (JWT, REST, WebSocket) |
| `apps/dashboard` | Next.js 15 (páginas de produção e plataforma) |

### Services
| Path | Função |
|------|--------|
| `services/workflow-engine` | Orquestração, templates, cancel, retry, callbacks |
| `services/agents-worker` | Handlers Celery unificados (V1+V2) |
| `services/ai-gateway` | Roteamento central de IA (:8020) |
| `services/research-agent` | Legado / template (worker unificado é o path ativo) |
| `services/_agent_template` | Template para novos agentes |

### Packages
| Path | Função |
|------|--------|
| `packages/ai-core` | Protocols, ProviderRegistry, RoutingService, adapters |
| `packages/ai-client` | HTTP client + Gateway*Provider |
| `packages/prompts` | Prompt Manager |
| `packages/models` | Model Manager |
| `packages/memory` | Memory Manager |
| `packages/cache` | Cache Manager |
| `packages/cost` | Cost Manager |
| `packages/events` | Event Bus |
| `packages/content-sources` | Content Sources |
| `packages/storage` | AssetManager, AssetPipelineService, AssetIndexService |
| `packages/analytics-ai` | Analytics AI |
| `packages/plugins-core` | Plugin Marketplace |
| `packages/shared` | Enums, base handlers, compat V1 |
| `packages/database` | SQLAlchemy models + Alembic |

---

## 2. Plataforma — inventário

| # | Módulo (visão V3) | Status | Paths principais | Gap |
|---|-------------------|--------|------------------|-----|
| 1 | AI Gateway | **EXISTS** | `services/ai-gateway`, `packages/ai-core`, `packages/ai-client` | — |
| 2 | ProviderRegistry | **EXISTS** | `ai-core/.../provider_registry.py`, `domain/registry.py` | — |
| 3 | Text / Speech / Subtitle providers | **EXISTS** | adapters em `ai-core/infrastructure/adapters/` | — |
| 4 | Vision / Image / Embedding providers | **EXISTS** | `adapters/vision`, `image`, `embedding` | Vision/embed dependem de modelos Ollama opcionais |
| 5 | ProviderFactory | **EXISTS** | `AIProviderFactory` + `shared/providers/factory.py` | Dual stack legado em `shared` (compat); gateway é default |
| 6 | RoutingService (Model Manager no gateway) | **EXISTS** | `ai-core/.../routing_service.py` | — |
| 7 | Workflow Engine | **EXISTS** | `services/workflow-engine` | Não é “V3 builder”; templates estáticos + DB |
| 8 | Workflow templates V1/V2 | **EXISTS** | `shared/workflow_templates.py` | Sem template `v3-*` ainda |
| 9 | Cancel / Delete pipeline | **EXISTS** | `pipelines.py`, `engine.cancel_pipeline` | — |
| 10 | Retry / DLQ quality→editor | **EXISTS** | `engine.py`, `quality.py`, score 0–10 | — |
| 11 | Prompt Manager | **EXISTS** | `packages/prompts`, `/prompts` | Sem classe `PromptEditor`; UI + service |
| 12 | Memory Manager | **EXISTS** | `packages/memory`, `/memory` | Cache in-process; sem Redis dedicado |
| 13 | Cost Manager | **EXISTS** (A4) | `packages/cost`, `/costs` | text + speech + subtitle + image |
| 14 | Cache Manager | **EXISTS** | `packages/cache`, `/cache` | Só respostas LLM text |
| 15 | Model Manager | **EXISTS** | `packages/models`, `/models` | — |
| 16 | Plugin Manager / Marketplace | **DONE** | Unified `/marketplace` + plugins install | `docs/MARKETPLACE.md` |
| 17 | Storage / AssetManager (MinIO) | **EXISTS** | `packages/storage` | Nome “StorageManager” não existe; `AssetManager` é a fachada |
| 18 | AssetPipelineService | **EXISTS** | `storage/.../asset_pipeline_service.py` | — |
| 19 | Asset Manager V2 (tags, hash, search, preview) | **EXISTS** (A2/A3) | `asset_index_service.py`, `/assets`, `/preview`, `/content` | Versionamento/histórico ainda pouco usados |
| 20 | Asset Search avançado | **EXISTS** (A2) | `asset_metadata.py`, `AssetSearchFilters`, `/assets/search` | Facets: theme, game, character, motion, color, objects |
| 21 | Event Bus | **EXISTS** (A1) | `packages/events` | Wire `snake.case`; aliases PascalCase em `PASCAL_CASE_ALIASES`; todos steps `v2-dynamic` mapeados |
| 22 | Content Sources | **EXISTS** | `packages/content-sources` (`SourceManager`, `SourceRegistry`) | Naming missão: ContentSourceManager = SourceManager |
| 23 | Clip Research Agent | **EXISTS** | `handlers/clip_research.py` | — |
| 24 | Asset Collector Agent | **PARTIAL** | `handlers/asset_collector.py` | Sem geração explícita de preview/thumbnail por asset coletado |
| 25 | Asset Index Agent | **EXISTS** | `handlers/asset_index.py` | — |
| 26 | Takes Manager (só seleção) | **EXISTS** | `handlers/takes.py` | — |
| 27 | Editor (FFmpeg) | **EXISTS** | `handlers/editor.py`, `ffmpeg_*` | Consome `director_plan` (B6); Ken Burns por cena |
| 28 | Quality Agent | **EXISTS** | `handlers/quality.py`, `docs/QUALITY.md` | Score 0–10 + dimensões técnicas |
| 29 | Publisher (dry-run + live OAuth) | **EXISTS** | `handlers/publisher.py`, `docs/PUBLISHING.md` | Live + OAuth via channels (Tier D4) |
| 30 | Thumbnail Agent | **EXISTS** | `handlers/thumbnail.py` | Via ImageProvider; sem composição AI avançada de frame |
| 31 | Analytics AI | **PARTIAL** | `handlers/analytics.py`, `packages/analytics-ai` | Insights estimados; auto-apply memory opt-in |
| 32 | Auth JWT | **EXISTS** | `apps/backend` auth routes | — |
| 33 | RBAC (roles) | **EXISTS** (A5+C2) | Org-scoped via `organization_members.role` + platform admin |
| 34 | Multi-tenant (orgs) | **EXISTS** (C1) | `Organization`, `OrganizationMember`, `org_id` em project/pipeline |
| 35 | Billing / Stripe | **DONE** | `billing_plans`, créditos, Stripe webhooks | `docs/BILLING.md` |
| 36 | Workflow Builder (drag-drop) | **DONE** | Custom org workflows + builder UI | `docs/WORKFLOW_BUILDER.md` |
| 37 | Scheduler | **DONE** | `pipeline_schedules`, cron runner | `docs/SCHEDULER.md` |
| 38 | API pública versionada (produto) | **EXISTS** | `/api/v1/*`, API keys C5, rate limit | — |
| 39 | Observabilidade Prometheus/Grafana/OTel | **EXISTS** | `/metrics`, Jaeger, dashboards Grafana | — |
| 40 | Kubernetes | **EXISTS** | `k8s/base`, KEDA overlays, staging | — |
| 41 | CI/CD | **EXISTS** | CI + deploy staging GHCR | — |

---

## 3. Dashboard

| Página | Rota | Status |
|--------|------|--------|
| Painel | `/` | EXISTS |
| Projetos | `/projects` | EXISTS |
| Produção (jobs, cancel/delete) | `/jobs` | EXISTS |
| Vídeos | `/videos` | EXISTS |
| Orquestração | `/workflow` | EXISTS (sem builder) |
| Fluxo | `/pipeline` | EXISTS |
| Agentes | `/agents` | EXISTS |
| Assets | `/assets` | EXISTS |
| Armazenamento | `/storage` | EXISTS |
| Fontes | `/content-sources` | EXISTS |
| Clip Research | `/clip-research` | EXISTS |
| Coletor | `/asset-collector` | EXISTS |
| AI Gateway | `/ai-gateway` | EXISTS |
| Provedores | `/providers` | EXISTS |
| Modelos | `/models` | EXISTS |
| Prompts | `/prompts` | EXISTS |
| Memória | `/memory` | EXISTS |
| Cache | `/cache` | EXISTS |
| Análises | `/analytics` | EXISTS |
| Custos | `/costs` | EXISTS |
| Eventos | `/events` | EXISTS |
| Logs | `/logs` | EXISTS |
| Plugins | `/plugins` | EXISTS |
| Configurações | `/settings` | EXISTS |
| Workflow Builder UI | `/workflows/builder` | **DONE** |
| Billing / Plans UI | Settings → Plano e créditos | **DONE** |
| Org / Team admin UI | — | **MISSING** |
| Scheduler UI | Projetos → Agendamentos | **DONE** |

---

## 4. Agentes / features V3 (novos)

| # | Feature | Status | Notas |
|---|---------|--------|-------|
| 1 | Storyboard AI | **EXISTS** (B4) | `handlers/storyboard.py`; frames framing/movement/transition |
| 2 | Scene Director | **EXISTS** (B5) | `handlers/scene_director.py`, `director_plan.py`; ritmo via emotion |
| 3 | Trend Intelligence | **EXISTS** (B9) | `handlers/trend_intelligence.py`; memória + analytics → research |
| 4 | Hook Generator | **EXISTS** (B1) | `handlers/hook.py`, template `v3-quality`, evento `hook.finished` |
| 5 | Emotion Analyzer | **EXISTS** (B3) | `handlers/emotion.py`, scores emotion/curiosity/retention/impact |
| 6 | Script Reviewer | **EXISTS** (B2) | `handlers/script_review.py`, evento `script_review.finished` |
| 7 | Video Reviewer (nota) | **EXISTS** (B7) | `handlers/video_review.py`; não falha pipeline (B8 usará score) |
| 8 | Auto Retry (nota &lt; 8) | **EXISTS** (B8) | Engine: `creative_retry.*`; budget `MAX_CREATIVE_RETRIES` |
| 9 | Eventos PascalCase (`ResearchFinished`) | **EXISTS** (aliases) | Wire permanece `snake.case`; `resolve_event_type` / `pascal_alias` |
| 10 | Eventos clip/asset/takes | **EXISTS** (A1) | `clip_research.finished`, `assets.ready`, `asset_index.finished`, `takes.finished` |

---

## 5. Eventos — mapa atual

Implementados em `packages/events/.../event_types.py`:

| Constante | Valor emitido |
|-----------|----------------|
| RESEARCH_FINISHED | `research.finished` |
| SCRIPT_FINISHED | `script.finished` |
| SCENE_CREATED | `scene.created` |
| VOICE_GENERATED | `voice.generated` |
| SUBTITLE_CREATED | `subtitle.created` |
| EDITOR_FINISHED | `editor.finished` |
| QUALITY_APPROVED | `quality.approved` |
| PUBLISHER_FINISHED | `publisher.finished` |
| THUMBNAIL_CREATED | `thumbnail.created` |
| ANALYTICS_PROCESSED | `analytics.processed` |

**Ausentes no mapa de steps:** `clip_research`, `asset_collector`, `asset_index`, `takes`.

**Decisão recomendada (ADR-003):** manter `snake.case` no wire format; documentar aliases PascalCase no PRD/EVENT docs (sem breaking change).

---

## 6. Resumo quantitativo

| Status | Quantidade (aprox.) |
|--------|---------------------|
| EXISTS | ~28 módulos/áreas |
| PARTIAL | ~14 |
| MISSING | ~12 (quase todos V3 criativo + SaaS comercial) |

**Conclusão:** a plataforma de produção automática **já é operacional**. O V3 é majoritariamente **inteligência criativa + SaaS comercial + ops enterprise**, não re-fundação.

---

## 7. O que NÃO fazer

- Não recriar AI Gateway, Prompt/Memory/Cache/Cost/Model Managers, Content Sources, Asset Pipeline, Dashboard pages existentes.
- Não renomear pacotes só por naming da missão (`SourceManager` permanece; documentado em NAMING.md).
- Não quebrar `v1-default` / `v2-dynamic`.
