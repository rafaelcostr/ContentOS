# Growth AI

Growth AI é o domínio estratégico de crescimento do ContentOS (`packages/growth/`).

Ele **não substitui** a fábrica de vídeos. Ele observa canais, competidores, learning, analytics, performance e publicação para **decidir** estratégia e recomendações. A execução permanece com Workflow, Scheduler e Publisher.

## Documentação

| Doc | Conteúdo |
|-----|----------|
| [GROWTH_OS_RULES.md](./GROWTH_OS_RULES.md) | Regras arquiteturais globais (10 regras) |
| [GROWTH_OS_ROADMAP.md](./GROWTH_OS_ROADMAP.md) | Roadmap de 18 fases |
| [GROWTH_AI_GAP_ANALYSIS.md](./GROWTH_AI_GAP_ANALYSIS.md) | Auditoria EXISTS / PARTIAL / MISSING |

## Regra central

> Nenhum módulo existente deve ser reescrito.
> Alterações só são permitidas quando aditivas, compatíveis e necessárias para expor dados/contratos ao Growth.

Ver [Regra 4](./GROWTH_OS_RULES.md#regra-4--evolução-aditiva-e-compatível).

## Mapeamento de entidades (não duplicar)

| Conceito | Implementação canônica |
|----------|------------------------|
| Canal social | `Channel` + `/api/v1/channels` |
| Conta conectada | `Channel.credentials` + OAuth |
| Perfil analítico | `growth_channel_profiles` / `ChannelProfile` |
| Identidade da marca | `project_memory` + Project DNA |
| Calendário de execução | `PipelineSchedule` |
| Calendário estratégico | `growth_content_calendar` |
| Posts texto | `multi_content` |
| Recomendações | `build_project_recommendations()` |

## Foundation implementada

- Pacote `packages/growth/`
- Domínio: `ChannelProfile`, `CompetitorProfile`, `GrowthReport`, `GrowthStrategy`, `ContentCalendar`, `AssetPerformance`, `GrowthRecommendation`
- Repository protocol + adapter SQLAlchemy
- Tabelas: `growth_channel_profiles`, `growth_competitors`, `growth_reports`, `growth_strategies`, `growth_recommendations`, `growth_asset_performance`, `growth_content_calendar`
- Migration `024_growth_foundation.py`
- Rotas:
  - `GET /api/v1/growth/channels?project_id=...`
  - `GET /api/v1/growth/competitors?project_id=...`
  - `POST /api/v1/growth/competitors`
  - `GET /api/v1/growth/report?project_id=...`
  - `GET /api/v1/growth/recommendations?project_id=...`
- Dashboard: `/growth`, `/channels`, `/competitors`, `/strategy` (foundation parcial)
- Testes: `tests/test_growth_foundation.py`

## Reuso de módulos existentes

| Área | Reuso |
|------|-------|
| Canais | `Channel` + OAuth + `/channels` |
| Recomendações | `contentos_intelligence.application.recommendations` |
| Performance | Performance Learning + Platform Analytics |
| Memória | Project Memory, Creative Memory, Knowledge Base |
| Publicação | Publisher + `platform_publications` |
| Assets | Asset Manager + Take Recommendation |
| Produção | Workflow Engine (`context_json`) |
| Agendamento | Scheduler (`PipelineSchedule`) |
| Posts | Multi Content + Multi Content Video |
| Tendências | Trend Intelligence + Trend Forecast |

## Garantias

- Nenhum workflow de vídeo foi alterado pela foundation Growth.
- Publisher, Learning, Analytics, Asset Manager, Editor e Quality não foram substituídos.
- Growth adiciona tabelas e APIs complementares.
- Growth decide; Workflow produz; Scheduler agenda; Publisher publica.

## Status atual

- **Fase 1 (Auditoria):** concluída
- **Fase 2 (Channel Registry):** concluída
- **Fase 3 (YouTube Integration):** concluída
- **Fase 4 (Channel Analyzer):** concluída — score, relatório, recomendações, histórico
- **Próxima fase:** Fase 5 — Brand Intelligence (aguardando aprovação)
