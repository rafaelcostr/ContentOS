# Growth OS — Regras Arquiteturais Globais

| Campo | Valor |
|-------|--------|
| **Domínio** | `packages/growth/` |
| **Papel** | Cérebro estratégico — decide, não executa |
| **Última revisão** | 2026-07-09 |

---

## Regras obrigatórias (todas as fases)

### Regra 1 — Auditar antes de implementar

Antes de qualquer código em uma fase:

1. Auditar o monorepo.
2. Classificar cada módulo como **EXISTS**, **PARTIAL** ou **MISSING**.
3. Atualizar `docs/GROWTH_AI_GAP_ANALYSIS.md`.

### Regra 2 — Nunca duplicar responsabilidades

Antes de criar entidade, tabela, rota ou serviço novo, verificar se já existe equivalente:

| Proposto | Usar em vez de criar |
|----------|----------------------|
| `SocialChannel` | `Channel` (`models.Channel`) |
| `ConnectedAccount` | `Channel.credentials` + OAuth existente |
| `ChannelProfile` | `growth_channel_profiles` (overlay analítico sobre `Channel.id`) |
| Brand Intelligence paralelo | `project_memory` + Project DNA |
| Post generation paralelo | `multi_content` + `multi_content_video` |
| Segundo scheduler | `PipelineSchedule` (execução) + `growth_content_calendar` (estratégia) |
| Segundo recommendation engine | `build_project_recommendations()` |

### Regra 3 — Nunca reescrever módulos existentes

Workflow Engine, AI Gateway, Publisher, Scheduler, Asset Manager, Learning, Memory, Knowledge Base, Creative Memory, Analytics, Content Score, Quality, Editor, Trend Intelligence, Recommendation Engine, Event Bus e Dashboard **não são substituídos**.

### Regra 4 — Evolução aditiva e compatível

> **Nenhum módulo existente deve ser reescrito.**
> Alterações em módulos existentes só são permitidas quando forem **aditivas**, **compatíveis** e **necessárias** para expor dados/contratos ao Growth.

Exemplos permitidos:

- Novo endpoint em `platform_analytics` para snapshots por canal
- Novo evento `growth.*` em `event_types.py`
- Novo handler Celery `channel_analyzer` (agente novo, não altera existentes)
- Campo opcional em `project_memory` para missão/valores (Fase 5)

Exemplos proibidos:

- Reescrever `Publisher` dentro de `packages/growth`
- Alterar assinatura pública de `/api/v1/channels`
- Growth enfileirar tasks Celery diretamente (bypass do Workflow Engine)

### Regra 5 — Não quebrar APIs públicas

Rotas, schemas e contratos existentes permanecem estáveis. Growth expõe rotas em `/api/v1/growth/*` e enriquece `/channels` apenas de forma compatível.

### Regra 6 — Separação decisão vs execução

| Módulo | Responsabilidade |
|--------|------------------|
| **Growth** | Decidir: estratégia, calendário, recomendações, plano |
| **Workflow Engine** | Produzir: pipelines de vídeo |
| **Scheduler** | Agendar: execução temporal |
| **Publisher** | Publicar: upload e metadados |
| **Analytics** | Coletar: métricas OAuth |
| **Learning / Memory** | Persistir: aprendizado |

Growth **nunca** substitui nenhum executor.

### Regra 7 — Uma fase por vez

Implementar uma fase, entregar testes + documentação, **parar e aguardar aprovação** antes da próxima.

### Regra 8 — Critério de alteração em módulo existente

Toda alteração fora de `packages/growth/` exige:

1. Justificativa no gap analysis da fase.
2. Contrato documentado (API, evento ou payload).
3. Teste de regressão (workflows `v1-default`, `v2-dynamic`, `factory-full` intactos).

### Regra 9 — Isolamento multi-canal

Toda query e persistência Growth deve ser filtrada por `org_id` → `project_id` → `channel_id` (quando aplicável).

### Regra 10 — Contrato Growth → Workflow

Growth inicia produção apenas via Workflow Engine, com `context_json` enriquecido:

```json
{
  "topic": "...",
  "objective": "...",
  "target_platform": "youtube",
  "channel_id": "...",
  "brand_context_ref": "project_memory",
  "growth_plan_id": "...",
  "tone": "...",
  "cta": "...",
  "duration_target_seconds": 45
}
```

---

## Documentos relacionados

- [GROWTH_OS_ROADMAP.md](./GROWTH_OS_ROADMAP.md) — roadmap de 18 fases
- [GROWTH_AI_GAP_ANALYSIS.md](./GROWTH_AI_GAP_ANALYSIS.md) — auditoria EXISTS/PARTIAL/MISSING
- [GROWTH_AI.md](./GROWTH_AI.md) — visão do domínio Growth
