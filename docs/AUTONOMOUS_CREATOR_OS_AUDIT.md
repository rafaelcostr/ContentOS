# Auditoria Arquitetural — Autonomous Creator OS

Data: 2026-07-09

Objetivo desta auditoria: transformar o prompt de evolução do ContentOS em um mapa arquitetural antes de novas implementações. Este documento classifica cada capacidade como `EXISTS`, `PARTIAL` ou `MISSING`, apontando onde o sistema já tem base, quais contratos devem ser reutilizados e quais lacunas ainda impedem o ContentOS de operar como um Autonomous Channel Operating System completo.

Regra central: não reconstruir módulos existentes. O Autopilot deve ser uma camada estratégica fina que pensa, decide e coordena, enquanto execução permanece em Workflow Engine, Scheduler, Publisher, Analytics, Memory, Learning, Knowledge Base, Asset Manager e demais módulos já existentes.

## Resumo Executivo

O ContentOS já está bem além de uma fábrica de vídeos. Ele possui pipeline de produção, Growth OS, inteligência de canal, memória de projeto/canal, analytics, learning, scheduler, publisher, dashboard e mecanismos de execução assistida.

O que já ficou bem encaminhado nas fases recentes:

- Status do Autopilot.
- Channel Intelligence Snapshot.
- Calendário autônomo incremental.
- Execução autônoma assistida com `dry_run`.
- Closed Learning Loop com recomendações para próximo ciclo.

Maiores lacunas atuais:

- Um domínio `packages/autopilot/` separado como camada estratégica oficial.
- Media Strategy Engine para decidir biblioteca própria, Pexels, Pixabay, IA imagem, IA vídeo, gameplay, motion, documentário ou mistura.
- Audience Intelligence explícita por canal.
- Creative Director superior antes do Editor, integrado ao Autopilot.
- Ciclos temporais pós-publicação em 24h, 48h, 7 dias e 30 dias.
- Sugestões versionadas de prompts sem alteração automática.
- Social Autopilot completo para reprogramar, republicar, criar continuações e adaptar conteúdo entre plataformas.

## Matriz Geral

| Capacidade | Status | Diagnóstico |
|---|---:|---|
| Workflow Engine | EXISTS | Módulo central já existe e deve continuar sendo executor. |
| Agentes de produção | EXISTS | Worker registra agentes de roteiro, cenas, editor, publisher, analytics, learning, channel analyzer e outros. |
| AI Gateway | EXISTS | Já documentado e exposto no dashboard. |
| Growth OS | EXISTS | Pacote `packages/growth` concentra estratégia, calendário, canais, competidores, performance e autopilot. |
| Learning Engine | EXISTS | Learning, Performance Learning e Creative Memory existem. |
| Knowledge Base | EXISTS | Knowledge/semantic search existem em `packages/intelligence`. |
| Project Memory | EXISTS | `packages/memory` e rotas `/memory`, `/brand`, `/dna`. |
| Channel Memory | EXISTS | `ChannelMemoryRow`, serviço e rotas dedicadas. |
| Publisher | PARTIAL | Existe, mas publicação real depende de OAuth/API/plataformas e `PUBLISH_MODE`. |
| OAuth | PARTIAL | Existe base e auditoria; configuração real é manual. |
| Scheduler | EXISTS | `PipelineSchedule`, rotas `/schedules` e bridge Growth. |
| Asset Manager | EXISTS | Assets, collections, sources e MinIO existem. |
| Analytics | EXISTS | Platform Analytics, Analytics AI e Performance Learning existem. |
| Dashboard | EXISTS | Muitas telas dedicadas já existem. |
| Autopilot estratégico isolado | PARTIAL | Lógica existe dentro de Growth; pacote `packages/autopilot/` ainda não existe. |

## 1. Channel Intelligence

Status: `PARTIAL`

Onde existe:

- `packages/growth/src/contentos_growth/application/channel_intelligence.py`
- `packages/growth/src/contentos_growth/application/channel_analyzer.py`
- `packages/growth/src/contentos_growth/application/platform_analyzers/`
- `packages/growth/src/contentos_growth/application/platform_overview.py`
- `packages/growth/src/contentos_growth/application/service.py`

APIs:

- `GET /api/v1/growth/channels`
- `GET /api/v1/growth/channels/overview`
- `GET /api/v1/growth/channels/{channel_id}/workspace`
- `GET /api/v1/growth/channels/{channel_id}/intelligence`
- Rotas específicas de plataforma como `youtube_channel.py` e `platform_analytics.py`.

Modelos/tabelas:

- `Channel`
- `GrowthChannelProfileRow`
- `ChannelMemoryRow`
- `GrowthReportRow`
- `PlatformAnalyticsSnapshot`/estruturas de analytics já existentes no pacote de intelligence/database.

Agentes:

- `ChannelAnalyzerAgentHandler`
- `MediaAnalyzeAgentHandler`
- agentes de analytics e learning associados.

Dashboards:

- `/channels`
- `/growth`
- `/performance`
- `/analytics`
- `/history`

Cobertura atual:

- Já consolida canal, plataforma, memória, performance, competidores, estratégia, riscos e oportunidades.
- Já calcula confiança e score.
- Já alimenta Channel Manager e Autopilot.

Lacunas:

- Análise profunda de identidade visual, thumbnails, playlists, comentários, crescimento e estilo ainda não está completamente normalizada em um perfil único.
- Precisa mapear sinais por janela temporal e por tipo de conteúdo.

Próxima fase indicada:

- Expandir o snapshot com campos versionados para `visual_profile`, `thumbnail_patterns`, `title_patterns`, `retention_patterns`, `comment_patterns` e `growth_velocity`.

## 2. Brand Intelligence / DNA

Status: `PARTIAL`

Onde existe:

- `packages/memory/src/contentos_memory/domain/project_memory.py`
- `packages/memory/src/contentos_memory/domain/brand_identity.py`
- `packages/memory/src/contentos_memory/domain/project_dna.py`
- `packages/memory/src/contentos_memory/domain/dna_v2.py`
- `packages/memory/src/contentos_memory/application/memory_service.py`

APIs:

- `GET /api/v1/projects/{project_id}/brand`
- `PATCH /api/v1/projects/{project_id}/brand`
- `GET /api/v1/projects/{project_id}/dna`
- `PATCH /api/v1/projects/{project_id}/dna`
- `GET /api/v1/projects/{project_id}/memory`
- `PUT /api/v1/projects/{project_id}/memory`

Modelos/tabelas:

- `ProjectMemory`

Dashboards:

- `/brand`
- `/memory`
- telas de projeto e configurações.

Cobertura atual:

- Já há memória de projeto, marca e DNA.
- Agentes já conseguem receber contexto de memória via prompts e serviços compartilhados.

Lacunas:

- O DNA pedido no prompt é mais rico: arquétipo, palavras proibidas/favoritas, nível emocional, músicas, fontes, transições, formatos preferidos e personalidade.
- Falta garantir que todos os agentes consumam automaticamente o mesmo contrato de DNA, não apenas parte do contexto.

Próxima fase indicada:

- Normalizar um contrato `BrandDNAContext` usado por Growth, prompts, editor, thumbnail, voice, scene director e publisher.

## 3. Audience Intelligence

Status: `PARTIAL`

Onde existe:

- `packages/growth/src/contentos_growth/application/channel_intelligence.py`
- `packages/growth/src/contentos_growth/application/performance_learning_interpreter.py`
- `packages/intelligence/src/contentos_intelligence/application/platform_analytics/`
- `packages/intelligence/src/contentos_intelligence/application/performance_learning/`

APIs:

- `POST /api/v1/platform-analytics/sync`
- `POST /api/v1/platform-analytics/channels/{channel_id}/sync`
- `GET /api/v1/platform-analytics/snapshots`
- `GET /api/v1/growth/performance`
- `POST /api/v1/growth/performance/sync`

Modelos/tabelas:

- analytics de plataforma
- `GrowthAssetPerformanceRow`
- `LearningInsightRow`

Dashboards:

- `/analytics`
- `/performance`
- `/growth`

Cobertura atual:

- Usa performance real quando existe.
- Resume CTR, retenção, top hooks, assets e plataformas.

Lacunas:

- Ainda não há um perfil explícito de público por canal com idade, localização, hábitos, assuntos favoritos e conversão.
- Falta armazenamento versionado de segmentos de audiência.

Próxima fase indicada:

- Criar `AudienceIntelligenceSnapshot` consumindo analytics, comentários, performance e memória, sem duplicar Performance Learning.

## 4. Competitor Intelligence

Status: `PARTIAL`

Onde existe:

- `packages/growth/src/contentos_growth/application/competitor_analyzer.py`
- `packages/growth/src/contentos_growth/application/competitor_fetcher.py`
- `packages/growth/src/contentos_growth/application/channel_intelligence.py`

APIs:

- `GET /api/v1/growth/competitors`
- `POST /api/v1/growth/competitors`
- `GET /api/v1/growth/competitors/{competitor_id}`
- `POST /api/v1/growth/competitors/{competitor_id}/sync`
- `POST /api/v1/growth/competitors/{competitor_id}/analyze`
- `POST /api/v1/growth/competitors/sync-all`

Modelos/tabelas:

- `GrowthCompetitorRow`
- `GrowthRecommendationRow`

Agentes:

- `CompetitorAnalyzerAgentHandler`

Dashboards:

- `/competitors`
- `/growth`

Cobertura atual:

- Já cadastra, sincroniza, analisa e gera recomendações.
- Já entra no Channel Intelligence e Growth Report.

Lacunas:

- Frequência, crescimento, séries, padrões visuais e calendário concorrente ainda precisam ficar mais estruturados.
- Falta comparação multi-janela e alertas de tendência por concorrente.

Próxima fase indicada:

- Expandir análise para `competitor_patterns`, `cadence`, `series`, `visual_style`, `growth_velocity` e `topic_gap`.

## 5. Strategy Engine

Status: `PARTIAL`

Onde existe:

- `packages/growth/src/contentos_growth/application/content_strategist.py`
- `packages/growth/src/contentos_growth/application/growth_report_builder.py`
- `packages/growth/src/contentos_growth/application/channel_manager.py`
- `packages/growth/src/contentos_growth/application/autopilot.py`

APIs:

- `GET /api/v1/growth/strategy`
- `POST /api/v1/growth/strategy/generate`
- `GET /api/v1/growth/recommendations`
- `GET /api/v1/growth/report`

Modelos/tabelas:

- `GrowthStrategyRow`
- `GrowthRecommendationRow`
- `GrowthReportRow`

Dashboards:

- `/strategy`
- `/recommendations`
- `/growth`

Cobertura atual:

- Gera estratégia, objetivos, cadência, campanhas e metas por canal.
- Usa memória, recomendações, oportunidades e performance.

Lacunas:

- Ainda não separa claramente objetivos mensais, semanais e diários.
- Campanhas/séries/quadros existem como sinais, mas não como entidade estratégica rica e acompanhável.

Próxima fase indicada:

- Criar um plano estratégico hierárquico: `monthly_goals`, `weekly_goals`, `daily_objectives`, `campaigns`, `series`, `content_pillars`.

## 6. Editorial Calendar

Status: `EXISTS`

Onde existe:

- `packages/growth/src/contentos_growth/application/autonomous_calendar.py`
- `packages/growth/src/contentos_growth/application/content_strategist.py`
- `packages/growth/src/contentos_growth/application/smart_scheduler_bridge.py`

APIs:

- `GET /api/v1/growth/calendar`
- `GET /api/v1/growth/calendar/autonomous-plan`
- `POST /api/v1/growth/calendar/autonomous-plan/apply`
- `POST /api/v1/growth/calendar/{calendar_item_id}/schedule`
- `POST /api/v1/growth/calendar/sync-schedules`

Modelos/tabelas:

- `GrowthContentCalendarRow`
- `PipelineSchedule`

Dashboards:

- `/calendar`
- `/strategy`
- `/growth`

Cobertura atual:

- Gera calendário e aplica novos itens sem apagar os antigos.
- Mantém `channel_id`, plataforma, tipo de conteúdo, data planejada e metadata.

Lacunas:

- Falta calendário multi-formato completo por plataforma: Stories, posts, vídeos longos, Reels, Shorts e variações derivadas com regras próprias.

Próxima fase indicada:

- Expandir tipos e quotas por plataforma usando `platform_registry`, sem duplicar scheduler.

## 7. Content Decision Engine

Status: `PARTIAL`

Onde existe:

- `packages/growth/src/contentos_growth/application/channel_manager.py`
- `packages/growth/src/contentos_growth/application/autonomous_execution.py`
- `packages/growth/src/contentos_growth/application/autopilot.py`

APIs:

- `GET /api/v1/growth/channels/{channel_id}/manager/plan`
- `POST /api/v1/growth/channels/{channel_id}/manager/run`
- `GET /api/v1/growth/autopilot/execution-plan`
- `POST /api/v1/growth/autopilot/run`

Modelos/tabelas:

- `GrowthContentCalendarRow`
- `GrowthChannelProfileRow`
- `GrowthStrategyRow`

Dashboards:

- `/growth`
- `/channels`
- `/calendar`

Cobertura atual:

- Decide ações por canal: produzir, agendar, gerar post, analisar.
- Agrega ações em plano de execução assistida.

Lacunas:

- Precisa escolher objetivo, CTA, ângulo, público e variação criativa por item antes de enviar ao Workflow Engine.

Próxima fase indicada:

- Adicionar `ContentDecision` como objeto explícito em metadata do calendário.

## 8. Media Strategy Engine

Status: `MISSING`

Onde existe parcialmente:

- `packages/content-sources/`
- `apps/backend/src/contentos_gateway/api/routes/content_sources.py`
- `services/agents-worker/src/contentos_agents/handlers/asset_collector.py`
- `services/agents-worker/src/contentos_agents/handlers/clip_research.py`
- `packages/intelligence/src/contentos_intelligence/application/asset_semantic_search.py`
- `packages/intelligence/src/contentos_intelligence/application/reuse_advisor.py`
- docs de Media/AI Director indicam direção, mas não formam um engine estratégico central.

APIs:

- `GET /api/v1/content-sources`
- `GET /api/v1/content-sources/health`
- `POST /api/v1/content-sources/search`
- rotas de assets e reuse.

Modelos/tabelas:

- `Asset`
- `AssetMediaProfile`
- `PipelineAssetCollection`

Agentes:

- `clip_research`
- `asset_collector`
- `asset_index`
- `media_analyze`
- `asset_search`

Dashboards:

- `/content-sources`
- `/assets`
- `/clip-research`
- `/asset-collector`

Lacuna principal:

- Falta um cérebro que escolha automaticamente entre biblioteca própria, Pexels, Pixabay, imagem IA, vídeo IA, gameplay, infográficos, motion graphics, documentário ou mistura percentual.

Próxima fase indicada:

- Implementar `MediaStrategyPlan` consumindo Content Sources, Asset Manager, Knowledge Base, Performance Learning e Brand DNA.
- Saída deve ser apenas decisão/metadata para os agentes existentes, não download/publicação direta.

## 9. Creative Director

Status: `PARTIAL`

Onde existe:

- `docs/AI_DIRECTOR.md`
- `apps/backend/src/contentos_gateway/api/routes/director.py`
- `services/agents-worker/src/contentos_agents/handlers/ai_director.py`
- `services/agents-worker/src/contentos_agents/handlers/scene_director.py`
- `services/agents-worker/src/contentos_agents/handlers/editor.py`
- `packages/shared/src/contentos_shared/audiovisual_qa.py`

APIs:

- `POST /api/v1/director/plan`

Agentes:

- `ai_director`
- `scene_director`
- `editor`
- `quality`
- `video_review`

Dashboards:

- `/director`

Cobertura atual:

- Existe direção/revisão, sinais fracos e integração com retry.

Lacunas:

- Ainda não está ligado como decisão criativa superior do Autopilot para cada item do calendário.
- Falta receber Brand DNA, Media Strategy e objetivo de Growth em um contrato único.

Próxima fase indicada:

- Criar `CreativeDirectionBrief` como saída do Autopilot para ser consumida por `scene_director`, `editor`, `thumbnail` e `ai_director`.

## 10. Closed Learning Loop

Status: `PARTIAL`

Onde existe:

- `packages/growth/src/contentos_growth/application/closed_loop.py`
- `packages/growth/src/contentos_growth/application/performance_learning_interpreter.py`
- `packages/growth/src/contentos_growth/application/growth_report_builder.py`
- `packages/intelligence/src/contentos_intelligence/application/performance_learning/`
- `apps/backend/src/contentos_gateway/api/routes/performance_learning.py`

APIs:

- `GET /api/v1/growth/autopilot/closed-loop`
- `POST /api/v1/growth/autopilot/closed-loop/sync`
- `GET /api/v1/growth/performance`
- `POST /api/v1/growth/performance/sync`
- `POST /api/v1/performance-learning/process`
- `GET /api/v1/performance-learning/insights`

Modelos/tabelas:

- `LearningInsightRow`
- `GrowthRecommendationRow`
- `GrowthReportRow`
- `GrowthAssetPerformanceRow`
- `ProjectMemory`
- `ChannelMemoryRow`

Dashboards:

- `/performance`
- `/learning`
- `/growth`
- `/history`
- `/creative-memory`

Cobertura atual:

- Interpreta performance e gera recomendações.
- Closed Loop gera aprendizados, bloqueios, próximos ciclos e recomendações.

Lacunas:

- Faltam janelas temporais automáticas de 24h, 48h, 7 dias e 30 dias.
- Falta atualização automática controlada de Project Memory, Channel Memory, Knowledge Base e Creative Memory com política de aprovação.
- Falta gerar sugestões versionadas para prompts sem alterar prompts automaticamente.

Próxima fase indicada:

- Criar `ClosedLoopCyclePolicy` e agendamentos via `PipelineSchedule`/Scheduler.

## 11. Social Autopilot

Status: `PARTIAL`

Onde existe:

- `packages/growth/src/contentos_growth/application/autonomous_execution.py`
- `packages/growth/src/contentos_growth/application/smart_scheduler_bridge.py`
- `packages/growth/src/contentos_growth/application/post_manager.py`
- `apps/backend/src/contentos_gateway/api/routes/publish.py`
- `packages/database/src/contentos_database/publish_credentials.py`

APIs:

- `GET /api/v1/publish/status`
- `GET /api/v1/publish/attempts`
- `GET /api/v1/publish/channels`
- `POST /api/v1/publish/channels/{channel_id}/disconnect`
- Growth run/dispatch/schedule endpoints.

Modelos/tabelas:

- `PlatformPublicationRow`
- `Channel`
- `PipelineSchedule`
- `GrowthContentCalendarRow`

Dashboards:

- componentes `PublishAttempts`
- `PublishConnections`
- `/settings`
- `/channels`
- `/growth`

Cobertura atual:

- Prepara/agendas/produz com segurança.
- Publicação real depende de modo, credenciais e providers.

Lacunas:

- Repostar, cancelar, alterar horário, criar continuações, adaptar por plataforma e detectar viral automaticamente ainda não estão fechados em uma política única.

Próxima fase indicada:

- Criar política `SocialAutopilotPolicy` que consome Publisher/Scheduler/Analytics e só executa em modo autorizado.

## 12. Community Intelligence

Status: `PARTIAL`

Onde existe:

- `packages/intelligence/src/contentos_intelligence/application/comment_analyzer/`
- `packages/intelligence/src/contentos_intelligence/application/community_agent/`
- `apps/backend/src/contentos_gateway/api/routes/community.py`
- rotas de comment analyzer existentes.

APIs:

- `POST /api/v1/community/drafts/generate`
- `GET /api/v1/community/drafts`
- `PATCH /api/v1/community/drafts/{draft_id}`

Modelos/tabelas:

- `CommentAnalysisRow`
- `CommunityReplyDraftRow`

Dashboards:

- `/community`

Cobertura atual:

- Já há análise de comentários e rascunhos.
- Não responde automaticamente sem aprovação.

Lacunas:

- Falta conectar Community Intelligence ao Autopilot/Growth para influenciar estratégia, calendário e FAQ.

Próxima fase indicada:

- Integrar resumos de comentários no Channel Intelligence e Audience Intelligence.

## 13. Multi Channel Brain

Status: `PARTIAL`

Onde existe:

- `packages/growth/src/contentos_growth/application/multi_channel_scope.py`
- `packages/growth/src/contentos_growth/application/channel_manager.py`
- `packages/growth/src/contentos_growth/application/autonomous_execution.py`
- `packages/growth/src/contentos_growth/application/channel_intelligence.py`

APIs:

- `GET /api/v1/growth/channels/overview`
- `GET /api/v1/growth/channels/{channel_id}/workspace`
- `GET /api/v1/growth/autopilot/status`
- `GET /api/v1/growth/autopilot/execution-plan`

Modelos/tabelas:

- `Channel`
- `GrowthChannelProfileRow`
- `ChannelMemoryRow`
- `GrowthContentCalendarRow`
- `GrowthStrategyRow`

Dashboards:

- `/channels`
- `/growth`
- `/calendar`

Cobertura atual:

- Filtra calendário, recomendações e performance por canal.
- Agrega ações multi-canal no plano de execução.

Lacunas:

- Ainda falta isolamento completo por canal para DNA, objetivos, concorrentes e calendário avançado.
- Precisa garantir que dezenas de canais tenham limites de custo, fila e prioridade separados.

Próxima fase indicada:

- Criar governança multi-canal: budgets, prioridades, limites, políticas e health por canal.

## 14. Segurança Arquitetural

Status: `PARTIAL`

Onde existe:

- `packages/growth/src/contentos_growth/application/growth_hardening.py`
- `packages/growth/src/contentos_growth/application/growth_readiness.py`
- `packages/growth/src/contentos_growth/infrastructure/growth_rate_limiter.py`
- dependências de `require_editor`, quotas, billing e org service nas rotas.

APIs:

- `GET /api/v1/growth/health`
- `GET /api/v1/growth/readiness`
- `GET /api/v1/growth/oauth-audit`

Modelos/tabelas:

- `Channel`
- billing/organizations existentes
- publication credentials

Cobertura atual:

- Rate limit, readiness, OAuth audit, billing/quota e permissões aparecem no fluxo Growth.
- `dry_run` é padrão em execução autônoma.

Lacunas:

- Falta um documento de contrato formal impedindo duplicação de Scheduler/Publisher/Workflow/Learning/Memory em `packages/autopilot/`.
- Falta teste arquitetural que garanta que Autopilot não chama Celery/agentes diretamente.

Próxima fase indicada:

- Criar `docs/AUTOPILOT_CONTRACT.md` e testes de fronteira arquitetural.

## 15. Domínio `packages/autopilot/`

Status: `MISSING`, com lógica já `PARTIAL` dentro de Growth.

Situação atual:

- As capacidades de autopilot foram implementadas dentro de `packages/growth/src/contentos_growth/application/`:
  - `autopilot.py`
  - `autonomous_calendar.py`
  - `autonomous_execution.py`
  - `closed_loop.py`

Opinião arquitetural:

- Isso é funcional e conservador, mas o prompt pede explicitamente `packages/autopilot/`.
- Criar o pacote faz sentido apenas como camada fina, sem mover tudo agora e sem duplicar lógica.

Proposta segura:

- Criar `packages/autopilot/` com adapters/read models que chamam GrowthService e módulos existentes.
- Não produzir vídeos.
- Não publicar.
- Não chamar agentes.
- Não criar tabelas próprias no início.
- Expor contratos estratégicos e políticas:
  - `AutopilotBrain`
  - `ContentDecision`
  - `MediaStrategyPlan`
  - `CreativeDirectionBrief`
  - `ClosedLoopCyclePolicy`

## Gaps Prioritários

### Fase A — Contrato Arquitetural do Autopilot

Status: recomendado antes de novas features.

Entregas:

- `docs/AUTOPILOT_CONTRACT.md`
- `packages/autopilot/` mínimo, se aprovado.
- Teste arquitetural garantindo que Autopilot não importa Worker/Celery/Publisher direto.

Impacto:

- Evita duplicação e protege o sistema antes de crescer.

### Fase B — Media Strategy Engine

Status: maior lacuna funcional.

Entregas:

- Planejador que decide fonte de mídia por conteúdo.
- Saída em metadata para `clip_research`, `asset_collector`, `asset_search`, `editor`.
- Suporte a mistura percentual entre biblioteca, Pexels, Pixabay, IA imagem, IA vídeo, gameplay e motion.

Impacto:

- Resolve o problema de depender sempre das mesmas fontes.

### Fase C — Creative Direction Brief

Status: alto impacto.

Entregas:

- Brief criativo antes do editor.
- Integração com Brand DNA, Media Strategy, Content Decision e AI Director.

Impacto:

- Melhora ritmo, legendas, transições, música e estilo por canal.

### Fase D — Audience Intelligence

Status: alto impacto para crescimento real.

Entregas:

- Snapshot de audiência por canal.
- Uso de analytics, comentários, retenção, CTR e horários.

Impacto:

- Estratégia deixa de ser só conteúdo e passa a ser público + canal.

### Fase E — Closed Loop Temporal

Status: necessário para autonomia real.

Entregas:

- Ciclos 24h, 48h, 7d, 30d.
- Recomendações versionadas.
- Atualizações assistidas de memórias.

Impacto:

- Fecha o ciclo de aprendizado de verdade.

## Decisão Recomendada

Antes de implementar mais features, seguir esta ordem:

1. Criar contrato arquitetural do Autopilot e testes de fronteira.
2. Criar `packages/autopilot/` como camada fina, sem duplicar Growth.
3. Implementar Media Strategy Engine.
4. Implementar Creative Direction Brief.
5. Implementar Audience Intelligence.
6. Implementar Closed Loop Temporal.
7. Evoluir Social Autopilot.

Critério de aceite para próximas fases:

- Cada fase deve listar arquivos alterados.
- Cada fase deve reutilizar módulos existentes.
- Cada fase deve ter testes.
- Cada fase deve documentar APIs impactadas.
- Nenhuma fase deve recriar Publisher, Scheduler, Workflow, OAuth, Analytics, Memory, Learning ou Knowledge Base.

