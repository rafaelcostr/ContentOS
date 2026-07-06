# ContentOS V3 — Roadmap de Evolução

| Campo | Valor |
|-------|--------|
| **Base** | [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) |
| **Produto** | [PRD.md](./PRD.md) |
| **Decisões** | [ADR.md](./ADR.md) |
| **Regra** | Só PARTIAL e MISSING. Sem reescrita de EXISTS. Aprovação humana entre fases. |

---

## Princípio de priorização

```
1. Estabilidade / observabilidade do que já roda (PARTIAL barato)
2. Valor criativo no vídeo (MISSING que o usuário sente)
3. SaaS comercial (tenant, billing)
4. Plataforma avançada (builder, scheduler, marketplace unificado)
5. Ops enterprise (Prometheus, OTel, HPA maduro)
```

---

## Tier 0 — Concluído (não reimplementar)

Plataforma V1/V2 operacional:

- AI Gateway + todos os provider types atuais  
- Workflow Engine + cancel/retry técnico  
- Prompt / Model / Memory / Cache / Cost  
- Content Sources + Clip Research + Asset Collector + Asset Index + Takes  
- AssetPipelineService (MinIO + PG + dedup)  
- Editor / Quality técnico / Publisher dry-run / Thumbnail / Analytics AI  
- Dashboard (incl. `/assets`, `/workflow`, `/ai-gateway`, …)  
- Auth JWT, API `/api/v1`, Docker, K8s base, CI  

Detalhes: [GAP_ANALYSIS.md](./GAP_ANALYSIS.md).

---

## Tier A — Fechar PARTIAL de alto impacto

**Objetivo:** pipeline V2 observável e assets pesquisáveis sem novos agentes.

| Fase V3 | Item | Status atual | Entrega | Esforço |
|---------|------|--------------|---------|---------|
| **A1** | Eventos de domínio V2 completos | **DONE** | Mapear `clip_research`, `asset_collector`, `asset_index`, `takes` (+ aliases PascalCase) | P |
| **A2** | Asset Search avançado | **DONE** | Filtros/metadata: tema, tags, jogo, personagem, movimento, cor, objetos (API + UI `/assets`) | M |
| **A3** | Asset previews | **DONE** | Presigned URLs + stream autenticado `/content`; UI `/assets` | M |
| **A4** | Cost Manager cobertura | **DONE** | `record_speech` / `record_subtitle` / `record_image` + voice/subtitle/thumbnail | P |
| **A5** | RBAC enforcement | **DONE** | `require_editor` / `require_admin` nas mutações; auth em rotas abertas | P |

**Critério de saída Tier A:** eventos V2 visíveis em `/events`; busca de assets com metadados estendidos; sem regressão E2E `v2-dynamic`.

---

## Tier B — Inteligência criativa (MISSING de produto)

**Objetivo:** melhorar qualidade do conteúdo, não só montar o vídeo.

| Fase V3 | Item | Status | Entrega | Esforço |
|---------|------|--------|---------|---------|
| **B1** | Hook Generator | **DONE** | Step `hook` + template `v3-quality`; script consome `selected_hook` | M |
| **B2** | Script Reviewer | **DONE** | Step `script_review` no `v3-quality`; sobrescreve `script` no payload | M |
| **B3** | Emotion Analyzer | **DONE** | Step `emotion` no `v3-quality`; scores no payload | M |
| **B4** | Storyboard AI | **DONE** | Step `storyboard` após `scene`; frames para Scene Director | G |
| **B5** | Scene Director | **DONE** | Step `scene_director`; `director_plan` → zoom/pan/ritmo | G |
| **B6** | Editor consome director | **DONE** | Editor aplica `director_plan` nos filtros FFmpeg | M |
| **B7** | Video Reviewer | **DONE** | Step `video_review` após quality; `video_score` / `video_review_passed` | M |
| **B8** | Auto Retry criativo | **DONE** | Engine rebobina de `script` se score baixo; `MAX_CREATIVE_RETRIES` | G |
| **B9** | Trend Intelligence | **DONE** | Step `trend_intelligence`; memória + analytics → `trend_context` | G |

**Critério de saída Tier B:** template `v3-quality` ou `v3-full` documentado; E2E opcional; custos limitados por pipeline.

**Ordem sugerida dentro de B:** B1 → B2 → B3 → B7 → B8 (valor rápido), depois B4 → B5 → B6 (mais pesado), B9 por último.

---

## Tier C — SaaS comercial (MISSING)

| Fase V3 | Item | Status | Entrega | Esforço |
|---------|------|--------|---------|---------|
| **C1** | Multi-tenant (Organization) | **DONE** | `organizations`, `organization_members`, `org_id` em project/pipeline | G |
| **C2** | RBAC por org | **DONE** | `require_editor` org-scoped; membership > global | M |
| **C3** | Billing Stripe | **DONE** | Planos, créditos, webhooks, checkout | G |
| **C4** | Quotas por plano | **DONE** | Pipelines/mês + concorrentes por org | M |
| **C5** | API keys públicas | **DONE** | Keys por org + rate limit + `X-API-Key` | M |

**Critério de saída Tier C:** duas orgs isoladas no mesmo deploy; cobrança em modo test Stripe.

**Ordem:** C1 → C2 → C5 → C3 → C4 (ADR-005).

---

## Tier D — Plataforma avançada (MISSING)

| Fase V3 | Item | Status | Entrega | Esforço |
|---------|------|--------|---------|---------|
| **D1** | Scheduler | **DONE** | Cron por projeto + runner no gateway | M |
| **D2** | Workflow Builder | **DONE** | UI drag-and-drop → `WorkflowDefinition` por org | G |
| **D3** | Marketplace unificado | **DONE** | Plugins + agents + workflows + remote | G |
| **D4** | Publisher live + OAuth | DONE | Além de dry-run | G |

---

## Tier E — Ops enterprise (PARTIAL → EXISTS)

| Fase V3 | Item | Status | Entrega | Esforço |
|---------|------|--------|---------|---------|
| **E1** | OpenTelemetry tracing | DONE | Traces gateway → engine → agents | M |
| **E2** | Prometheus metrics | DONE | Export `/metrics` Prometheus-format | M |
| **E3** | Grafana dashboards | DONE | Manifests / docs | P |
| **E4** | K8s HPA workers | DONE | Pools por fila + KEDA / CPU HPA | M |
| **E5** | CI deploy | DONE | Pipeline deploy staging | M |

---

## Mapa Master Prompt V3 → este roadmap

| Fases do Master Prompt | Destino |
|------------------------|---------|
| 1 (docs) | **Este pacote** (PRD, ROADMAP, ADR, GAP) |
| 2–14 (plataforma core) | Tier 0 EXISTS / Tier A PARTIAL |
| 15–25 (criativo + analytics) | Tier B (+ Analytics já EXISTS) |
| 26 (dashboard) | Tier 0 EXISTS; gaps em Tier C/D UIs |
| 27–30 (builder, scheduler, API pública, marketplace) | Tier D (+ C5) |
| 31–32 (tenant, billing) | Tier C |
| 33–35 (obs, k8s, ci) | Tier E |

---

## Tier F — ContentOS V4 (Inteligência de Conteúdo)

**Status:** Epic 0 (fundação documental) **DONE** — aguardando implementação V4.0.1.

| Documento | Conteúdo |
|-----------|----------|
| [V4_ROADMAP.md](./V4_ROADMAP.md) | Fases V4.0–V4.3, ordem de epics, critérios de saída |
| [V4_CONSOLIDATION_MAP.md](./V4_CONSOLIDATION_MAP.md) | Mapeamento V3→V4 (EXTEND / COMPOSE / NEW) |
| [ADR-008](./ADR.md#adr-008--v4-inteligência-aditiva-e-pacote-único) | Princípios V4 aditivos |

**Status V4:** **COMPLETO** (V4.0–V4.3).

Opcional pós-V4: analytics OAuth, novos formatos, specialists adicionais.

**Opcional V3 (paralelo):** Analytics ML, validação E2E full stack, deploy production workflow.

---

## Como avançar uma fase

1. Você aprova o ID (ex.: `A1`).  
2. Agente: impacto → lista de arquivos → implementação mínima → testes → docs.  
3. Para e espera próxima aprovação.  
4. Nunca pular para MISSING de outro tier sem fechar o acordado.
