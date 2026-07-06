# ContentOS — Roadmap de Desenvolvimento

Desenvolvimento em fases. **Nunca avançar sem validar a fase anterior.**

---

## Fase 1 — Fundação ✅

**Objetivo:** Arquitetura sólida, infra local, auth, dashboard base.

| Entrega | Status |
|---------|--------|
| Monorepo Clean Architecture | ✅ |
| Docker Compose (Postgres, Redis, MinIO) | ✅ |
| Models SQLAlchemy (16+ tabelas) | ✅ |
| JWT + Refresh Token + RBAC | ✅ |
| Dashboard base (tema escuro, sidebar) | ✅ |
| Provider Protocols + Factory (DI) | ✅ |
| Plugin Registry (stub) | ✅ |
| Documentação (ARCHITECTURE, PHASES, PROVIDERS) | ✅ |

**Validação:** `docker compose up`, login, criar projeto, ver dashboard.

---

## Fase 2 — Stack IA Local ✅

**Objetivo:** Zero custo por vídeo — Ollama, Piper, Whisper local.

| Entrega | Status |
|---------|--------|
| Docker: Ollama + pull modelo | ✅ |
| Docker: Piper TTS service | ✅ |
| Docker: Whisper faster-whisper worker | ✅ |
| Health checks dos providers | ✅ |
| E2E pipeline script | ✅ |
| Testes integração providers | ✅ |

**Validação:** `python scripts/wait_for_services.py` → `python scripts/e2e_pipeline.py`

Ver [LOCAL_STACK.md](./LOCAL_STACK.md).

---

## Fase 3 — Pipeline Completo ✅

**Objetivo:** 9 agentes produzindo vídeo 1080x1920 real.

| Entrega | Status |
|---------|--------|
| Research → Publisher sequencial | ✅ |
| FFmpeg editor (zoom, fade, música, progress bar) | ✅ |
| Quality check + retry loop | ✅ |
| Upload takes por categoria | ✅ |
| Job page tempo real | ✅ |

**Validação:** `python scripts/e2e_pipeline.py` → ver vídeo em `/videos` e `/jobs`

Ver [EDITOR.md](./EDITOR.md).

---

## Fase 4 — Dashboard Produção ✅

**Objetivo:** Observabilidade completa.

| Entrega | Status |
|---------|--------|
| CPU/RAM/GPU metrics | ✅ |
| Agents page (modelo, fila, logs) | ✅ |
| Analytics por provider | ✅ |
| WebSocket pipeline visual | ✅ |
| Infra: Redis, Postgres, Celery | ✅ |

Ver [OBSERVABILITY.md](./OBSERVABILITY.md).

---

## Fase 5 — Plugins & Publicação ✅

**Objetivo:** Extensibilidade sem alterar núcleo.

| Entrega | Status |
|---------|--------|
| TikTok Plugin | ✅ |
| YouTube Shorts Plugin | ✅ |
| Instagram Reels Plugin | ✅ |
| Publisher + post_publish hook | ✅ |
| API channels + plugins | ✅ |
| Dashboard /plugins | ✅ |

Ver [PLUGINS.md](./PLUGINS.md).

**Modo padrão:** `PUBLISH_MODE=dry_run` — prepara metadados sem postar.

---

## Fase 6 — CI/CD & E2E ✅

| Entrega | Status |
|---------|--------|
| GitHub Actions (lint, test, build, docker) | ✅ |
| Testes E2E Playwright | ✅ |
| API integration tests | ✅ |
| Deploy K8s (manifests + HPA) | ✅ |

Ver [CI_CD.md](./CI_CD.md) e [K8S.md](./K8S.md).

---

## Roadmap completo ✅

Fases 1–6 (V1) e Fase 7 (V2) concluídas. ContentOS pronto para produção local e deploy K8s.

---

## Fase 7 — ContentOS V2 ✅

**Objetivo:** Expandir V1 sem quebrar o pipeline de 9 steps — AI Gateway, Event Bus, content sources, marketplace, pipeline dinâmico.

| Entrega | Status |
|---------|--------|
| AI Gateway + ai-core | ✅ |
| Prompt / Model / Memory / Cache / Cost Managers | ✅ |
| Event Bus (Redis Streams + PostgreSQL) | ✅ |
| Analytics AI + Thumbnail | ✅ |
| Plugin Marketplace | ✅ |
| Content Sources + Clip Research + Asset Collector | ✅ |
| Asset Manager V2 (dedup, tags, search) | ✅ |
| Workflow templates (`v1-default`, `v2-full`, `v2-dynamic`) | ✅ |
| Pipeline dinâmico 14 steps | ✅ |
| Dashboard V2 (páginas + seletor de workflow) | ✅ |
| K8s ai-gateway + CI job test-v2 | ✅ |
| Migration Alembic `003_v2_schema` | ✅ |
| Guias de extensão (`docs/guides/`) | ✅ |

**Validação:**

```powershell
# Migrations (DB existente)
cd packages/database
alembic upgrade head

# E2E V1 (padrão)
python scripts/e2e_pipeline.py

# E2E V2 dynamic (14 steps)
$env:E2E_WORKFLOW = "v2-dynamic"
python scripts/e2e_pipeline.py
```

Ver [ARCHITECTURE_V2.md](./ARCHITECTURE_V2.md), [V2_MIGRATION.md](./V2_MIGRATION.md) e [guides/](./guides/).

---

## Fase 8 — Asset Pipeline End-to-End 🚧

**Objetivo:** Content Sources → Asset Collector → PostgreSQL → Asset Index → Takes com dedup global.

| Entrega | Status |
|---------|--------|
| `AssetPipelineService` (MinIO + PG persist) | ✅ |
| `AssetCollector` persiste `Asset` rows + hash dedup | ✅ |
| `AssetIndex` tagga assets reais no DB | ✅ |
| Fila Celery `contentos.asset_index` no Dockerfile | ✅ |
| Quality aceita legendas via arquivo sem `segments` | ✅ |
| Editor repassa `segments` / refs ao payload | ✅ |
| Testes `test_asset_pipeline.py` | ✅ |

**Validação:**

```powershell
$env:DEFAULT_WORKFLOW = "v2-dynamic"
$env:E2E_WORKFLOW = "v2-dynamic"
python scripts/e2e_pipeline.py
pytest tests/test_asset_pipeline.py -v
```

---

## Fase 9 — Unificação AI Gateway ✅

**Objetivo:** Um único caminho de IA; Model Manager roteia por agente no gateway.

| Entrega | Status |
|---------|--------|
| `ProviderRegistry` unificado em `ai-core` | ✅ |
| `RoutingService` (Model Manager por agente) | ✅ |
| `AIService` usa registry + routing | ✅ |
| Gateway providers passam `agent=` | ✅ |
| Fallback direto sem recursão | ✅ |
| `USE_AI_GATEWAY=true` default no código e compose | ✅ |
| AI Gateway com models/database (DB routing) | ✅ |
| Endpoint `GET /v1/providers/resolve` | ✅ |
| Testes `test_ai_gateway_routing.py` | ✅ |

**Validação:**

```powershell
pytest tests/test_ai_gateway.py tests/test_ai_gateway_routing.py -v
curl "http://localhost:8020/v1/providers/resolve?agent=script&provider_type=text"
```

---

## Fase 10 — Providers avançados ✅

**Objetivo:** Image, Vision e Embedding via AI Gateway.

| Entrega | Status |
|---------|--------|
| Protocols Image/Vision/Embedding | ✅ (já existiam) |
| `LocalImageAdapter` (Pillow 1080x1920) | ✅ |
| `OllamaVisionAdapter` (llava) | ✅ |
| `OllamaEmbeddingAdapter` | ✅ |
| Registry + routing para image/vision/embedding | ✅ |
| Rotas `/v1/image`, `/v1/vision`, `/v1/embeddings` | ✅ |
| Gateway client providers | ✅ |
| Thumbnail agent via ImageProvider | ✅ |
| Testes `test_advanced_providers.py` | ✅ |

**Validação:**

```powershell
pytest tests/test_advanced_providers.py -v
curl -X POST http://localhost:8020/v1/image/generate -H "Content-Type: application/json" -d "{\"provider\":\"local\",\"prompt\":\"GTA 6\",\"agent\":\"thumbnail\"}" --output thumb.jpg
```

---

## Fase 11 — Dashboard completo ✅

**Objetivo:** Páginas da missão, workflow V2 e navegação por bounded context.

| Entrega | Status |
|---------|--------|
| Página `/assets` (busca, tags, hash, versão) | ✅ |
| `api.tagAsset` + Asset interface expandida | ✅ |
| `/workflow` com diagrama V1/V2 (14 steps) | ✅ |
| `V2PipelineDiagram` component | ✅ |
| Sidebar por seções (Produção, Conteúdo, IA, Observabilidade) | ✅ |
| Polling reduzido (analytics, events, agents, collectors) | ✅ |

**Validação:** abrir `http://localhost:3000/assets` e `http://localhost:3000/workflow`

---

## Fase 12 — Documentação & naming ✅

**Objetivo:** Docs refletem 100% o código das Fases 8–11.

| Entrega | Status |
|---------|--------|
| README atualizado (V2, estrutura, rotas) | ✅ |
| FLOW.md com pipeline 14 steps + mermaid | ✅ |
| NAMING.md (missão ↔ código) | ✅ |
| API.md (endpoints principais) | ✅ |
| AI_GATEWAY.md (image/vision/embedding + routing) | ✅ |
| Guias ADD_PROVIDER / ADD_CONTENT_SOURCE corrigidos | ✅ |
| ASSET_MANAGER_V2.md + AssetPipelineService | ✅ |
| ARCHITECTURE_V2 status Fases 7–12 | ✅ |

**Validação:** ler `README.md`, `docs/FLOW.md`, `docs/NAMING.md`, `docs/API.md`, `docs/guides/`.

---

## Roadmap pós-missão / ContentOS V3

Fases 1–12 cobrem a plataforma modular V1/V2.

**V3 não reescreve o core.** Auditoria e plano:

| Doc | Conteúdo |
|-----|----------|
| [PRD.md](./PRD.md) | Produto V3 |
| [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) | EXISTS / PARTIAL / MISSING |
| [ROADMAP.md](./ROADMAP.md) | Tiers A–E (só gaps) |
| [ADR.md](./ADR.md) | Decisões (evolução, eventos, tenant, auto-retry) |

**A1 concluído** — eventos de domínio V2 completos.

**A2 concluído** — Asset Search avançado.

**A3 concluído** — Asset previews.

**A4 concluído** — Cost Manager (speech/subtitle/image).

**A5 concluído** — RBAC enforcement (`docs/RBAC.md`).

**Tier C2 concluído** — RBAC por org (membership > role global).

**Próxima (opcional):** Analytics ML ou validação E2E full stack.

