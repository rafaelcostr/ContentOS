# ContentOS V3 — Product Requirements Document (PRD)

| Campo | Valor |
|-------|--------|
| **Produto** | ContentOS — Sistema Operacional de Conteúdo |
| **Versão do PRD** | 3.0 |
| **Data** | 2026-07-03 |
| **Status** | Auditoria concluída — sem implementação de features novas |
| **Base** | V1 + V2 em produção local (Fases 1–12 do ciclo anterior) |

---

## 1. Visão

ContentOS é uma plataforma SaaS em que o usuário informa um **tema** (ex.: `"GTA 6"`) e o sistema executa um **pipeline de agentes de IA** até entregar um vídeo curto pronto (1080×1920, 60 fps, H.264), com metadados de publicação, thumbnail e insights.

**V3** eleva a plataforma de “fábrica de vídeos automatizada” para **SaaS enterprise**: qualidade criativa mensurável, multi-tenant, billing, workflows configuráveis e observabilidade de produção.

---

## 2. Problema

Criar shorts em escala exige pesquisa, roteiro, mídia, voz, legendas, edição e validação. Ferramentas manuais não escalam. O ContentOS automatiza a linha de montagem com agentes **desacoplados**, preparados para milhares de usuários.

---

## 3. Princípios não negociáveis

1. Nenhum agente chama outro agente.
2. Toda orquestração passa pelo **Workflow Engine**.
3. Toda IA passa pelo **AI Gateway** (padrão).
4. Storage apenas via **AssetManager / AssetPipelineService** (nunca MinIO direto nos agentes).
5. Expandir sem remover V1/V2 (`v1-default`, `v2-dynamic`).
6. Clean Architecture, SOLID, DDD, Repository, Factory, Strategy, Adapter, DI, Event Driven.

---

## 4. Personas

| Persona | Necessidade |
|---------|-------------|
| **Creator solo** | Tema → vídeo em minutos, custo baixo (stack local) |
| **Agência / time** | Multi-projeto, memória de marca, custos por pipeline |
| **Empresa (V3)** | Org, RBAC, billing, scheduler, SLA, auditoria |

---

## 5. Escopo do produto (estado atual vs V3)

### 5.1 Já entregue (V1/V2) — baseline

- Pipeline V1 (9 steps) e V2 Dynamic (14 steps)
- AI Gateway + providers (text, speech, subtitle, image, vision, embedding)
- Prompt / Model / Memory / Cache / Cost Managers
- Event Bus, Content Sources, Clip Research, Asset Collector, Asset Index
- Asset Manager V2 (hash, tags, busca básica, persistência PG)
- Takes (seleção), Editor, Quality, Publisher (dry-run), Thumbnail, Analytics AI
- Dashboard enterprise parcial (páginas de plataforma)
- Auth JWT, API REST + Swagger, Docker, K8s base, CI

### 5.2 V3 — valor novo (a construir)

| Área | Requisitos |
|------|------------|
| **Inteligência criativa** | Hook Generator, Script Reviewer, Storyboard AI, Scene Director, Emotion Analyzer, Video Reviewer, Auto Retry com nota mínima e teto de custo |
| **Assets** | Busca avançada (tema, tags, cor, personagem, jogo, movimento); previews; histórico de versões usado de ponta a ponta |
| **Eventos** | Cobertura completa de steps V2/V3; aliases canônicos documentados |
| **SaaS** | Multi-tenant (orgs), RBAC real por recurso, Billing (Stripe), créditos |
| **Plataforma** | Workflow Builder (drag-and-drop), Scheduler, Marketplace unificado |
| **Ops** | Prometheus, Grafana, OpenTelemetry; K8s HPA maduro |

### 5.3 Fora de escopo imediato

- Reescrita do Workflow Engine ou AI Gateway
- Remoção de templates V1/V2
- Publicação live obrigatória (dry-run permanece default até OAuth/billing)

---

## 6. Fluxo principal (usuário)

1. Login / (V3) seleção de organização  
2. Criar projeto (memória de marca)  
3. Escolher workflow (`v1-default` | `v2-dynamic` | futuros `v3-*`)  
4. Informar tema → pipeline inicia  
5. Acompanhar em Produção (Parar / Excluir)  
6. Consumir vídeo, assets, custos, eventos, insights  

---

## 7. Requisitos funcionais prioritários (V3)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-01 | Pipeline V2 permanece estável e documentado | P0 |
| RF-02 | Eventos de domínio para todos os steps do pipeline ativo | P0 |
| RF-03 | Asset Search avançado sobre índice existente | P1 |
| RF-04 | Agentes de qualidade criativa (hook → review → storyboard → director) | P1 |
| RF-05 | Video Reviewer + Auto Retry com limites | P1 |
| RF-06 | Multi-tenant (Organization) + membership | P1 |
| RF-07 | RBAC por org (admin/editor/viewer em recursos) | P1 |
| RF-08 | Billing Stripe (planos, créditos) | P2 |
| RF-09 | Scheduler de pipelines | P2 |
| RF-10 | Workflow Builder visual | P2 |
| RF-11 | Observabilidade Prometheus/OTel | P2 |
| RF-12 | Marketplace unificado (plugins + agents + workflows) | P3 |

---

## 8. Requisitos não funcionais

| ID | Requisito |
|----|-----------|
| RNF-01 | Horizontal scaling de workers Celery por fila |
| RNF-02 | Isolamento de dados por tenant (V3) |
| RNF-03 | Idempotência de jobs e dedup de assets por hash |
| RNF-04 | Timeouts e teto de custo por pipeline (especialmente Auto Retry) |
| RNF-05 | Compatibilidade retroativa de APIs públicas existentes |

---

## 9. Métricas de sucesso (V3)

- Taxa de pipelines `completed` sem intervenção  
- Nota média do Video Reviewer (quando existir)  
- Custo médio por vídeo (Cost Manager)  
- Tempo p95 por workflow  
- (SaaS) MRR, churn, créditos consumidos  

---

## 10. Dependências e riscos

| Risco | Mitigação |
|-------|-----------|
| Loops de Auto Retry caros | Max retries, budget USD/tokens, circuit breaker |
| Multi-tenant tardio | Introduzir `org_id` cedo em Tier SaaS |
| Duplicar módulos V2 | Gap analysis obrigatória antes de cada fase |
| Qualidade LLM inconsistente | Prompts versionados + scores + fallback |

---

## 11. Documentos relacionados

- [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) — inventário EXISTS / PARTIAL / MISSING  
- [ROADMAP.md](./ROADMAP.md) — ordem de evolução  
- [ADR.md](./ADR.md) — decisões arquiteturais  
- [FLOW.md](./FLOW.md) — pipelines atuais  
- [NAMING.md](./NAMING.md) — missão ↔ código  
