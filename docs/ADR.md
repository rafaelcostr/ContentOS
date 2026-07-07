# ContentOS — Architecture Decision Records (ADR)

Registros de decisões arquiteturais. Novas decisões V3 começam em ADR-001 (ciclo V3); decisões históricas V1/V2 estão implícitas no código e resumidas abaixo.

| ID | Título | Status | Data |
|----|--------|--------|------|
| ADR-000 | Princípios fundacionais (V1/V2) | Aceito | 2026 |
| ADR-001 | V3 é evolução, não greenfield | Aceito | 2026-07-03 |
| ADR-002 | Priorizar PARTIAL/MISSING apenas | Aceito | 2026-07-03 |
| ADR-003 | Formato de eventos de domínio | Aceito | 2026-07-03 |
| ADR-004 | Storage facade = AssetManager | Aceito | 2026-07-03 |
| ADR-005 | Multi-tenant antes de billing público | Aceito | 2026-07-03 |
| ADR-006 | Auto Retry com orçamento | Aceito | 2026-07-03 |
| ADR-007 | Templates de workflow aditivos | Aceito | 2026-07-03 |
| ADR-008 | V4 inteligência aditiva e pacote único | Aceito | 2026-07-06 |

---

## ADR-000 — Princípios fundacionais (V1/V2)

### Contexto
Sistema multi-agente para produção de vídeos curtos.

### Decisão
- Agentes nunca se comunicam entre si.
- Orquestração exclusiva via Workflow Engine (Celery + callback HTTP).
- IA via AI Gateway (`USE_AI_GATEWAY=true` por padrão).
- Storage via `AssetManager` / `AssetPipelineService`.
- Pacotes por bounded context (Clean Architecture / DDD).
- Templates `v1-default`, `v2-full`, `v2-dynamic`.

### Consequências
Base estável; V3 deve estender, não substituir.

---

## ADR-001 — V3 é evolução, não greenfield

### Contexto
Master Prompt V3 lista “criar” AI Gateway, Memory, Event Bus, etc., mas o monorepo já implementa a maior parte.

### Decisão
Tratar V3 como **elevação a SaaS enterprise** sobre V1/V2. Fase de auditoria (PRD, ROADMAP, ADR, GAP) precede qualquer feature. Proibido reimplementar módulos **EXISTS**.

### Consequências
Menor risco de regressão; roadmap foca em gaps reais.

---

## ADR-002 — Priorizar apenas PARTIAL e MISSING

### Contexto
Recursos limitados; 35 fases lineares são inviáveis.

### Decisão
Ordem de trabalho:
1. Fechar **PARTIAL** de alto impacto (eventos V2, asset search, RBAC fino).
2. Entregar **MISSING** de valor de produto (agentes criativos).
3. Entregar **MISSING** SaaS (orgs, billing, scheduler, builder).
4. Ops enterprise (OTel, HPA maduro).

Cada fase: impacto → arquivos → implementação → testes → docs → aprovação.

### Consequências
Roadmap enxuto; ver [ROADMAP.md](./ROADMAP.md).

---

## ADR-003 — Formato de eventos de domínio

### Contexto
Missão V3 usa PascalCase (`ResearchFinished`). Código usa `snake.case` (`research.finished`).

### Decisão
- **Wire format permanece** `resource.action` em minúsculas (Redis Streams, PG, API).
- Documentar **aliases PascalCase** na documentação de eventos.
- Completar `STEP_TO_DOMAIN_EVENT` para steps V2 faltantes (`clip_research`, `asset_collector`, `asset_index`, `takes`) sem renomear eventos existentes.

### Consequências
Sem breaking change para consumidores atuais.

---

## ADR-004 — Storage facade = AssetManager

### Contexto
Missão pede “Storage Manager”. Código tem `AssetManager` (MinIO) + `AssetPipelineService` (MinIO + PG).

### Decisão
Não criar classe `StorageManager` redundante. `AssetManager` é o Storage Provider; `AssetPipelineService` é o use case de persistência de pipeline. Documentar em NAMING.md.

### Consequências
Menos abstrações; agentes continuam usando as APIs atuais.

---

## ADR-005 — Multi-tenant antes de billing público

### Contexto
Billing sem isolamento de org gera dívida técnica.

### Decisão
Introduzir `Organization` + membership + `org_id` em projetos/pipelines/assets **antes** de Stripe público e marketplace comercial. RBAC atual (`UserRole`) evolui para papéis **por organização**.

### Consequências
Billing e quotas por tenant ficam corretos desde o início do Tier SaaS.

---

## ADR-006 — Auto Retry com orçamento

### Contexto
Video Reviewer + “nota &lt; 8 → re-render” pode loopar e estourar custo/CPU.

### Decisão
Implementado (Tier B8):
- Nota mínima: `VIDEO_REVIEW_MIN_SCORE` (default 8) via `video_review_passed`.
- `MAX_CREATIVE_RETRIES` (default 1) em `pipeline.retry_count`.
- Rewind a partir de `CREATIVE_RETRY_FROM` (default `script`).
- Circuit breaker: após limite, emite `creative_retry.exhausted` e segue para `publisher` (não falha o pipeline).

### Consequências
Qualidade sobe sem loop infinito; custo limitado ao número de retries.

---

## ADR-007 — Templates de workflow aditivos

### Contexto
Novos agentes (hook, storyboard, director, reviewers) não devem quebrar V2.

### Decisão
Novos steps entram em templates novos (`v3-quality`, `v3-full`) ou flags em `WorkflowDefinition.config`. `v1-default` e `v2-dynamic` permanecem.

### Consequências
Usuários opt-in para pipelines mais longos/caros.

---

## ADR-008 — V4 inteligência aditiva e pacote único

### Contexto
O Master Prompt V4 propõe 12 epics (Viral Intelligence, Knowledge Base, Multi Content, etc.). O monorepo V3 já implementa hook, emotion, trend_intelligence, memory, quality_scoring, video_review, analytics-ai e embeddings. Implementar cada epic como silo isolado duplicaria scoring, memória e steps de pipeline.

### Decisão
1. **V4 é 100% aditivo** — templates `v1-default`, `v2-dynamic`, `v3-quality` permanecem inalterados.
2. **Pacote único** `packages/intelligence/` (`contentos_intelligence`) concentra interfaces e orquestração V4; epics são submódulos, não pacotes paralelos concorrentes.
3. **Consolidação V3→V4** documentada em [V4_CONSOLIDATION_MAP.md](./V4_CONSOLIDATION_MAP.md): EXTEND > COMPOSE > NEW.
4. **Step composto** `content_intelligence` — um job Celery orquestra reuse + viral (+ futuro A/B preview) antes do editor; evita proliferar steps no pipeline.
5. **Template opt-in** `v4-intelligence` = `v3-quality` + `content_intelligence` (ADR-007).
6. **Project DNA** estende `ProjectMemory` — sem tabela `project_dna` paralela.
7. **Content Score 0–100** é fachada (`ContentScoreService`) sobre quality, video_review e viral_report — não substitui scores existentes.
8. **Ordem de implementação** definida em [V4_ROADMAP.md](./V4_ROADMAP.md): DNA → KB → Reuse → Viral (V4.0), depois A/B, Score, Specialists (V4.1).
9. Cada fase V4: impacto → ADR se necessário → docs → código → testes → Swagger/dashboard → aprovação humana.

### Consequências
- Menor risco de regressão V1/V2/V3.
- Epics V4 compartilham contratos DI; módulos não dependem diretamente uns dos outros.
- Dashboard executivo (Epic 12) só após APIs V4.0–V4.2 estáveis.
- Learning Engine documenta limitação sem métricas externas de plataforma até integração futura.

---

## ADR-009 — Aquisição de mídia licenciada (V5.0)

### Contexto
O clip pipeline V2 (`clip_research` → `asset_collector`) só buscava biblioteca local e assets do projeto. Para autonomia real (“tema → vídeo com B-roll”), é necessário download de vídeos de fontes externas **com licença clara**.

### Decisão
1. **Estender** `packages/content-sources/` — não criar pacote paralelo.
2. Adapters oficiais **Pexels** e **Pixabay** com `license_type` em metadata.
3. `DownloadPipeline` centraliza HTTP fetch, limite de tamanho (`MEDIA_MAX_DOWNLOAD_MB`) e validação de licença (`MEDIA_ALLOWED_LICENSES`).
4. **Proibido** scrape TikTok/redes sociais ou serviços de remoção de marca d’água.
5. `asset_collector` coleta top-N candidatos por cena (`MEDIA_COLLECT_TOP_N`) para enriquecer biblioteca.
6. Dedup global via SHA-256 existente no `AssetPipelineService`.

### Consequências
- Pipeline autônomo com B-roll royalty-free.
- Dependência de API keys Pexels/Pixabay (free tier).
- Media Intelligence (V5.0.3) indexará assets já adquiridos por este pipeline.

---

## Como adicionar um ADR

1. Incrementar ID.
2. Seções: Contexto, Decisão, Consequências, Status.
3. Linkar no ROADMAP quando a decisão destravar uma fase.
