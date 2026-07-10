# Growth OS — Roadmap (18 Fases)

| Campo | Valor |
|-------|--------|
| **Objetivo** | Transformar ContentOS em Sistema Operacional de crescimento de canais |
| **Domínio novo** | `packages/growth/` (cérebro estratégico) |
| **Última revisão** | 2026-07-09 |
| **Regras** | [GROWTH_OS_RULES.md](./GROWTH_OS_RULES.md) |

---

## Mapa geral

| Fase | Nome | Status atual | Próximo passo |
|------|------|--------------|---------------|
| 1 | Auditoria Arquitetural | **CONCLUÍDA** | — |
| 2 | Channel Registry | **CONCLUÍDA** | — |
| 3 | YouTube Integration | **CONCLUÍDA** | — |
| 4 | Channel Analyzer | **CONCLUÍDA** | Aprovação para Fase 5 |
| 5 | Brand Intelligence | PARTIAL | Estender Project DNA |
| 6 | Channel Memory | MISSING | Nova camada por `channel_id` |
| 7 | Competitor Intelligence | PARTIAL | CRUD existe; análise MISSING |
| 8 | Growth Report | PARTIAL | Consumir módulos reais |
| 9 | Content Strategist AI | MISSING | Novo agente |
| 10 | Content Factory Integration | PARTIAL | Contrato `context_json` |
| 11 | Multi Platform | PARTIAL | YouTube first; demais EXISTS em OAuth |
| 12 | Post Manager | PARTIAL | Orquestrar Multi Content |
| 13 | Smart Scheduler | PARTIAL | Bridge calendar → PipelineSchedule |
| 14 | Performance Learning | EXISTS | Growth interpreta (não recoleta) |
| 15 | Channel Manager AI | MISSING | Novo agente diário |
| 16 | Multi Channel | PARTIAL | Isolamento por canal |
| 17 | Growth Dashboard | PARTIAL | 4 páginas; 6+ faltando |
| 18 | Hardening Final | PARTIAL | E2E, OAuth audit, docs |

---

## Fase 1 — Auditoria Arquitetural ✅

**Objetivo:** entender o que já existe antes de implementar.

**Entregas:**

- Relatório EXISTS / PARTIAL / MISSING → `docs/GROWTH_AI_GAP_ANALYSIS.md`
- Mapa de módulos e dependências
- Riscos de duplicação documentados
- Regras globais → `docs/GROWTH_OS_RULES.md`
- Roadmap formalizado → este documento

**Status:** concluída. Nenhuma feature nova implementada.

---

## Fase 2 — Channel Registry ✅

**Objetivo:** cadastro central de canais sociais.

**Entidades (mapeamento canônico — não criar duplicatas):**

| Conceito do roadmap | Implementação |
|---------------------|---------------|
| `SocialChannel` | `Channel` existente |
| `ConnectedAccount` | `Channel.credentials` + OAuth |
| `ChannelProfile` | `growth_channel_profiles` (overlay analítico) |
| `GrowthReport` | `GrowthReport` (domínio Growth) |

**APIs:**

| Rota | Status |
|------|--------|
| `GET /channels` | EXISTS |
| `GET /channels/{id}` | EXISTS |
| `POST /channels` | EXISTS |
| `PUT /channels/{id}` | EXISTS |
| `DELETE /channels/{id}` | EXISTS |

**Dashboard:** `/channels` — CRUD completo (criar, editar, ativar/desativar, remover, status OAuth).

**Testes:** `tests/test_channels_api.py`

**Status:** concluída.

---

## Fase 3 — YouTube Integration ✅

**Objetivo:** conectar e sincronizar YouTube real.

**Reuso:** OAuth existente, `refresh_channel_token_if_needed`, `platform_analytics`.

**Entregas:**

| Item | Rota / módulo |
|------|----------------|
| Status da conexão | `GET /api/v1/channels/{id}/youtube/status` |
| Sincronizar canal | `POST /api/v1/channels/{id}/youtube/sync` |
| Dados salvos | `GET /api/v1/channels/{id}/youtube/data` |
| Fetcher YouTube | `platform_analytics/youtube.py` |
| Persistência | `platform_analytics_snapshots` (overview + mídia) |

**Dados coletados:** canal (bio, branding, inscritos), playlists, vídeos, Shorts (≤60s), métricas básicas.

**Dashboard:** painel YouTube em `/channels` com botão sincronizar.

**Testes:** `tests/test_youtube_integration.py`

**Status:** concluída. Sem lógica Growth ainda.

---

## Fase 4 — Channel Analyzer ✅

**Objetivo:** análise inteligente do canal conectado.

**Agente:** `channel_analyzer` (Celery, fora do pipeline de vídeo)

**Analisa:** bio, branding, thumbnails, frequência, playlists, duração, Shorts, hashtags, CTA, tom, público provável.

**Entregas:**

| Item | Local |
|------|-------|
| Motor de análise | `packages/growth/application/channel_analyzer.py` |
| Persistência | `growth_channel_profiles`, `growth_reports`, `growth_recommendations` |
| APIs | `POST/GET /channels/{id}/analyze`, `GET .../analysis/history` |
| Evento | `channel.analyzed` |
| Dashboard | botão **Analisar canal** em `/channels` |

**Testes:** `tests/test_channel_analyzer.py`

**Status:** concluída.

---

## Fase 5 — Brand Intelligence

**Objetivo:** identidade da marca por projeto.

**Direção:** estender `project_memory` / Project DNA — **não** criar módulo paralelo.

**Campos MISSING:** missão, objetivos, valores, regras editoriais formais.

**Integração:** `BaseAgentHandler.render_prompt()` já injeta DNA.

---

## Fase 6 — Channel Memory

**Objetivo:** memória isolada por canal.

**Escopo:** vídeos vencedores/ruins, hooks, CTAs, temas, horários, hashtags, insights.

**Separação:**

- Project Memory → identidade da marca
- Channel Memory → padrões por canal
- Creative Memory → contexto de pipelines
- Knowledge Base → indexação semântica

---

## Fase 7 — Competitor Intelligence

**Objetivo:** cadastrar e analisar concorrentes.

**EXISTS:** `growth_competitors`, CRUD API, dashboard.

**MISSING:** fetch de métricas, análise de padrões, jobs de sync.

---

## Fase 8 — Growth Report

**Objetivo:** relatório estratégico consolidado.

**Growth consome (sem reescrever):** Analytics, Learning, Publisher, Memory, Content Score, Quality, Asset Manager, Trend Intelligence.

**Entregas:** Growth Report real, Content Recommendations (delegar ao recommendation engine), Asset Ranking, Channel Health, Oportunidades, Riscos.

---

## Fase 9 — Content Strategist AI

**Objetivo:** plano de conteúdo automático.

**Entregas:** plano semanal/mensal, cadência vídeos/posts, horários, campanhas, objetivos por canal.

**Persistência:** `growth_strategies`, `growth_content_calendar`.

---

## Fase 10 — Content Factory Integration

**Objetivo:** Growth manda demanda ao Workflow.

Growth envia via `POST /internal/pipelines` com `context_json`. Workflow produz normalmente.

---

## Fase 11 — Multi Platform

**Ordem:** YouTube → Instagram → TikTok → Facebook → Threads → Pinterest → LinkedIn → X.

OAuth e Publisher já suportam YouTube, TikTok, Instagram. Expandir analytics e fetchers por plataforma.

---

## Fase 12 — Post Manager

**Objetivo:** conteúdo além de vídeo.

**Reuso:** `multi_content`, `multi_content_video`. Post Manager = orquestração Growth + adaptação por plataforma.

---

## Fase 13 — Smart Scheduler

**Objetivo:** calendário inteligente.

Growth decide **quando**; `PipelineSchedule` + `scheduler_service` executam.

Modos: manual, assistido, automático.

---

## Fase 14 — Performance Learning

**Objetivo:** aprendizado pós-publicação.

**EXISTS:** `PerformanceLearningService`, sync OAuth, indexação KB + memory.

Growth **interpreta**; não duplica coleta.

---

## Fase 15 — Channel Manager AI

**Objetivo:** agente gerente diário do canal.

Lê: analytics, learning, memory, competitors, calendar, trends, assets.

Decide e envia planos ao Workflow/Scheduler — **nunca** enfileira Celery diretamente.

---

## Fase 16 — Multi Channel

**Objetivo:** dezenas de canais isolados.

Cada canal: brand (projeto), channel memory, analytics, learning, calendário, estratégia, assets, competidores.

Filtro obrigatório: `org_id` → `project_id` → `channel_id`.

---

## Fase 17 — Growth Dashboard

**Telas:**

| Tela | Status |
|------|--------|
| Channels | PARTIAL |
| Growth | EXISTS |
| Brand | MISSING (usar `/projects` + DNA) |
| Competitors | EXISTS |
| Calendar | MISSING |
| Strategy | PARTIAL |
| Recommendations | PARTIAL |
| Performance | MISSING |
| Publishing | EXISTS (`/plugins`) |
| History | MISSING |

---

## Fase 18 — Hardening Final

Testes E2E Growth, rate limits, auditoria de tokens OAuth, tratamento de falhas, backups, documentação operacional.

---

## Execução

1. Uma fase por vez.
2. Auditoria → arquitetura → implementação → testes → docs → **parar**.
3. Aguardar aprovação antes da próxima fase.
