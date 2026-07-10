# Mapa de Fases — Autonomous Creator Operating System

Data: 2026-07-09

Este mapa usa o prompt revisado do Autopilot com duas regras adicionais:

1. Os "novos domínios" representam capacidades estratégicas, não necessariamente pacotes, tabelas ou serviços novos.
2. Antes de criar qualquer domínio físico, verificar se a capacidade pode ser entregue como contrato, read model, adapter, policy, metadata ou extensão aditiva de módulo existente.

O objetivo é levar o ContentOS a 100% como Autonomous Creator Operating System sem reconstruir módulos maduros e sem duplicar responsabilidades.

## Princípio Arquitetural

O Autopilot Brain observa, aprende, pensa, planeja e delega.

Ele nunca:

- chama Worker diretamente;
- chama Celery diretamente;
- publica;
- produz vídeos;
- baixa mídia;
- recria Scheduler;
- recria Publisher;
- recria Analytics;
- recria Memory;
- recria Learning;
- recria Knowledge Base;
- recria Workflow Engine.

Execução sempre fica com os módulos existentes.

## Estado Atual

Já existem ou estão bem encaminhados:

- Workflow Engine;
- AI Gateway;
- agentes de produção;
- Growth OS;
- Channel Intelligence;
- Brand/Project/Channel Memory;
- Scheduler;
- Publisher em modo controlado;
- Platform Analytics;
- Performance Learning;
- Creative Memory;
- Knowledge Base;
- Asset Manager;
- Content Sources;
- Dashboard;
- Growth Autopilot Status;
- Calendário Autônomo;
- Execução Autônoma Assistida;
- Closed Learning Loop inicial.

Principais lacunas:

- contrato formal do Autopilot;
- pacote `packages/autopilot/` como camada estratégica fina;
- testes arquiteturais de fronteira;
- Media Strategy Engine;
- Creative Direction Brief;
- Audience Intelligence;
- Objective Engine hierárquico;
- Digital Twin por canal;
- Market/Trend Intelligence avançado;
- Cost Intelligence;
- Resource Manager;
- Closed Learning Temporal;
- Prompt Evolution versionado;
- Social Autopilot completo;
- Governance multi-canal.

## Critérios De 100%

O ContentOS será considerado 100% dentro desta arquitetura quando:

- cada canal conectado tiver um Twin estratégico vivo;
- cada conteúdo planejado estiver ligado a um objetivo superior;
- o sistema decidir conteúdo, mídia, estilo, calendário e execução em modo assistido/automático;
- o sistema souber quando não executar por custo, recurso, risco ou falta de dados;
- o sistema aprender em ciclos 24h, 48h, 7d e 30d;
- o sistema gerar sugestões versionadas de prompt, sem sobrescrever automaticamente;
- o sistema operar vários canais com budget, prioridade, health e fila independentes;
- a publicação real continuar passando por Publisher/OAuth/autorização;
- testes garantirem que Autopilot não executa responsabilidades proibidas.

## Fase 0 — Contrato Arquitetural Do Autopilot

Status alvo: obrigatório antes de novas features.

Objetivo:

- formalizar o que o Autopilot pode e não pode fazer;
- impedir duplicação de Workflow, Scheduler, Publisher, Analytics, Memory e Learning;
- criar testes arquiteturais de fronteira.

Entregas:

- `docs/AUTOPILOT_CONTRACT.md`;
- testes verificando imports proibidos;
- lista de dependências permitidas;
- matriz de responsabilidades;
- definição dos contratos estratégicos iniciais.

Arquivos prováveis:

- `docs/AUTOPILOT_CONTRACT.md`;
- `tests/test_autopilot_architecture.py`.

Não deve criar:

- tabelas;
- endpoints grandes;
- agentes;
- workers;
- chamadas diretas para Celery/Publisher.

Critério de aceite:

- testes passam;
- documento deixa claro que Autopilot só decide e delega;
- nenhuma feature funcional nova ainda.

## Fase 1 — `packages/autopilot/` Como Camada Fina

Objetivo:

- criar o domínio físico mínimo do Autopilot sem mover código existente;
- expor contratos/read models/policies;
- reutilizar GrowthService e módulos existentes.

Entregas:

- pacote mínimo `packages/autopilot/`;
- `AutopilotBrain`;
- `AutopilotDecision`;
- `AutopilotContext`;
- adapters para Growth;
- documentação de fronteira.

Arquivos prováveis:

- `packages/autopilot/pyproject.toml`;
- `packages/autopilot/src/contentos_autopilot/__init__.py`;
- `packages/autopilot/src/contentos_autopilot/domain.py`;
- `packages/autopilot/src/contentos_autopilot/brain.py`;
- `packages/autopilot/src/contentos_autopilot/adapters/growth.py`;
- `tests/test_autopilot_brain.py`.

Reutiliza:

- `contentos_growth.application.service.GrowthService`;
- Growth Autopilot Status;
- Autonomous Calendar;
- Autonomous Execution;
- Closed Loop.

Critério de aceite:

- pacote não importa worker, Celery, Publisher direto ou agentes;
- brain retorna decisões, não executa;
- testes arquiteturais passam.

## Fase 2 — Objective Engine

Objetivo:

- garantir que todo conteúdo exista por causa de um objetivo superior.

Hierarquia:

- Company Goals;
- Project Goals;
- Channel Goals;
- Monthly Goals;
- Weekly Goals;
- Daily Goals;
- Campaigns;
- Series;
- Videos/Posts.

Entregas:

- contrato `ObjectiveTree`;
- policy de priorização;
- ligação entre objetivos e calendário;
- metadata no `GrowthContentCalendarRow`;
- APIs de leitura/planejamento, se necessário.

Reutiliza:

- `GrowthStrategyRow`;
- `GrowthRecommendationRow`;
- `GrowthContentCalendarRow`;
- Strategy Engine atual;
- Dashboard `/strategy`.

Critério de aceite:

- novo calendário autônomo carrega `objective_id`/`objective_path` em metadata;
- nenhum vídeo planejado fica sem objetivo;
- testes cobrem objetivo mensal/semanal/diário.

## Fase 3 — Digital Twin Por Canal

Objetivo:

- criar um modelo vivo por canal que reúna estado estratégico sem duplicar memórias.

O Twin conhece:

- histórico;
- marca/DNA;
- concorrentes;
- performance;
- audiência;
- comentários;
- estilo;
- campanhas;
- séries;
- objetivos;
- custos;
- aprendizados.

Entregas:

- `ChannelTwinSnapshot`;
- adapter que compõe dados de Growth, Memory, Analytics, Learning e Community;
- endpoint de leitura;
- dashboard ou seção em `/channels`.

Reutiliza:

- `Channel`;
- `GrowthChannelProfileRow`;
- `ChannelMemoryRow`;
- `ProjectMemory`;
- `GrowthStrategyRow`;
- `GrowthCompetitorRow`;
- `LearningInsightRow`;
- `CommentAnalysisRow`.

Critério de aceite:

- Twin é read model;
- não cria memória paralela;
- cada decisão estratégica consulta o Twin ou seus adapters.

## Fase 4 — Audience Intelligence

Objetivo:

- criar snapshot rico de audiência por canal consumindo analytics, comentários e performance.

Campos:

- idade, sexo, localização, idioma quando disponível;
- interesses;
- CTR;
- retenção;
- tempo médio;
- comentários;
- horários;
- dispositivos;
- segmentos;
- comportamentos;
- assuntos favoritos.

Entregas:

- `AudienceIntelligenceSnapshot`;
- integração com Channel Intelligence;
- recomendações por segmento;
- influência no calendário e objetivos.

Reutiliza:

- Platform Analytics;
- Performance Learning;
- Community Intelligence;
- Channel Memory.

Critério de aceite:

- sem duplicar Analytics;
- se não houver dados reais, reporta confiança baixa e próximos passos;
- influencia `ContentDecision`.

## Fase 5 — Market Intelligence E Trend Engine

Objetivo:

- detectar oportunidades de mercado e tendências sem copiar concorrentes.

Fontes possíveis:

- Google Trends;
- TikTok Trends;
- YouTube Trends;
- Reddit;
- X/Twitter;
- News;
- Steam;
- IMDb;
- Amazon;
- App Store;
- Play Store;
- keywords;
- eventos;
- sazonalidade.

Entregas:

- `MarketSignal`;
- `TrendOpportunity`;
- `SaturationSignal`;
- ranking de oportunidades;
- integração com Objective Engine e calendário.

Reutiliza:

- Trend Intelligence atual;
- Competitor Intelligence;
- Knowledge Base;
- Content Sources quando aplicável.

Critério de aceite:

- fontes externas são adapters opcionais;
- ausência de API externa não quebra o sistema;
- oportunidades entram como recomendações, não execução automática.

## Fase 6 — Media Strategy Engine

Objetivo:

- decidir automaticamente a estratégia de mídia para cada conteúdo.

Opções:

- biblioteca própria;
- assets internos;
- gameplay;
- Pexels;
- Pixabay;
- IA imagem;
- IA vídeo;
- motion graphics;
- documentário;
- infográficos;
- mistura percentual.

Entregas:

- `MediaStrategyPlan`;
- `MediaSourceMix`;
- score de risco/licença;
- score de custo;
- metadata para `clip_research`, `asset_collector`, `asset_search` e `editor`.

Reutiliza:

- Asset Manager;
- Content Sources;
- Knowledge Base;
- Asset Search;
- Download Pipeline;
- AI Gateway apenas via providers existentes.

Critério de aceite:

- Autopilot não baixa mídia;
- apenas gera plano;
- agentes existentes executam coleta/uso;
- cada item do calendário pode receber `media_strategy`.

## Fase 7 — Visual Intelligence

Objetivo:

- estudar vídeos e extrair padrões visuais reutilizáveis.

Extrair:

- ritmo;
- transições;
- zoom;
- cores;
- motion;
- tipografia;
- efeitos;
- enquadramento;
- legendas;
- velocidade;
- cortes;
- estilo visual.

Entregas:

- `VisualPatternSnapshot`;
- padrões por canal;
- ligação com Channel Twin e Creative Director.

Reutiliza:

- `media_analyze`;
- `AssetMediaProfile`;
- Video Review;
- AI Director;
- Audiovisual QA.

Critério de aceite:

- padrões são read models;
- não duplica AI Director;
- alimenta Creative Direction Brief.

## Fase 8 — Creative Direction Brief

Objetivo:

- gerar um brief criativo superior antes da produção.

Entrada:

- Brand DNA;
- Audience;
- Objective;
- Trend;
- Media Strategy;
- Market;
- Performance;
- Visual Intelligence.

Saída:

- `CreativeDirectionBrief`;
- `SceneBrief`;
- `ThumbnailBrief`;
- `MusicBrief`;
- `VoiceBrief`;
- `TransitionBrief`;
- `EditorBrief`.

Reutiliza:

- AI Director;
- Scene Director;
- Editor;
- Thumbnail;
- Voice;
- Quality;
- Video Review.

Critério de aceite:

- brief entra em `context_json` do Workflow;
- agentes existentes consomem o brief;
- Autopilot não edita vídeo.

## Fase 9 — Cost Intelligence

Objetivo:

- considerar custo em toda decisão estratégica.

Perguntas:

- vale usar modelo caro?
- vale usar modelo local?
- vale gerar vídeo IA?
- vale reutilizar asset?
- vale renderizar agora?
- vale gerar narração?

Entregas:

- `CostDecisionScore`;
- previsão de custo por plano;
- recomendação de modo econômico/normal/agressivo;
- integração com billing/quotas.

Reutiliza:

- Billing;
- Costs dashboard;
- AI Gateway provider resolution;
- Resource usage;
- Pipeline credit cost.

Critério de aceite:

- decisões do Autopilot incluem `cost_score`;
- se custo ultrapassar limite, gera bloqueio ou aprovação manual.

## Fase 10 — Resource Manager

Objetivo:

- decidir quando executar considerando recursos reais.

Conhece:

- GPU;
- VRAM;
- CPU;
- RAM;
- workers;
- Celery;
- storage;
- bandwidth;
- tokens;
- API limits;
- fila.

Entregas:

- `ResourceReadiness`;
- `ExecutionWindowRecommendation`;
- bloqueios por recurso;
- integração com Scheduler.

Reutiliza:

- Metrics;
- Prometheus;
- Celery/worker status apenas por leitura;
- Scheduler;
- dashboard `/metrics`, `/ops`, `/jobs`.

Critério de aceite:

- Autopilot não controla worker diretamente;
- apenas recomenda/agendada quando recursos estão saudáveis.

## Fase 11 — Closed Learning Temporal

Objetivo:

- fechar ciclos automáticos pós-publicação em 24h, 48h, 7 dias e 30 dias.

Entregas:

- `ClosedLoopCyclePolicy`;
- agendamentos via Scheduler;
- comparação com objetivos;
- recomendações versionadas;
- atualização assistida de memória.

Reutiliza:

- Closed Loop atual;
- Performance Learning;
- Platform Analytics;
- Scheduler;
- Growth Reports;
- Memory.

Critério de aceite:

- ciclos são agendados sem recriar Scheduler;
- resultados entram em Growth History;
- não altera prompts automaticamente.

## Fase 12 — Prompt Evolution

Objetivo:

- criar sugestões versionadas de prompts com aprovação e rollback.

Todo prompt deve possuir:

- versão;
- histórico;
- score;
- motivo da alteração;
- autor;
- aprovação;
- rollback.

Entregas:

- `PromptSuggestion`;
- scoring baseado em performance;
- API para aprovar/rejeitar sugestão;
- dashboard em `/prompts`.

Reutiliza:

- Prompt Manager atual;
- Prompt versions;
- Performance Learning;
- Creative Memory.

Critério de aceite:

- nunca sobrescreve prompt automaticamente;
- toda sugestão é versionada;
- rollback testado.

## Fase 13 — Community Intelligence Integrada

Objetivo:

- transformar comentários em inteligência estratégica.

Gerar:

- FAQ;
- dores;
- objeções;
- pedidos;
- novos vídeos;
- novas campanhas;
- atualização de Audience Intelligence.

Reutiliza:

- Comment Analyzer;
- Community Agent;
- Community drafts;
- Audience Intelligence;
- Knowledge Base.

Critério de aceite:

- não responde automaticamente sem configuração explícita;
- insights influenciam objetivos/calendário.

## Fase 14 — Social Autopilot

Objetivo:

- planejar operações sociais sem publicar sem autorização.

Planeja:

- repost;
- crosspost;
- stories;
- threads;
- community posts;
- continuações;
- clipes;
- vídeos derivados.

Reutiliza:

- Publisher;
- Scheduler;
- Platform Analytics;
- Calendar;
- Growth Execution.

Critério de aceite:

- modo padrão assistido;
- publicação live exige OAuth, provider e autorização;
- gera plano e usa Publisher existente.

## Fase 15 — Governance Multi-Canal

Objetivo:

- administrar dezenas/centenas de canais com segurança.

Cada canal possui:

- budget;
- limites;
- prioridade;
- quotas;
- custos;
- health;
- fila;
- SLA.

Entregas:

- `ChannelGovernancePolicy`;
- health e prioridade por canal;
- bloqueios por budget/quota;
- visão consolidada multi-canal.

Reutiliza:

- Billing;
- Quotas;
- Organizations;
- Channel Workspace;
- Scheduler;
- Growth Overview.

Critério de aceite:

- decisões respeitam limites por canal;
- dashboard mostra riscos e prioridades.

## Fase 16 — Event Driven Coordination

Objetivo:

- desacoplar coordenação estratégica por eventos quando fizer sentido.

Eventos candidatos:

- `StrategyGenerated`;
- `CampaignCreated`;
- `ContentApproved`;
- `MediaSelected`;
- `VideoRejected`;
- `TrendDetected`;
- `LearningCompleted`;
- `AudienceChanged`;
- `WorkflowCompleted`;
- `PublisherCompleted`.

Regra:

- eventos são preferenciais para comunicação assíncrona;
- chamadas diretas são permitidas para leitura, composição de read models e serviços de aplicação existentes.

Reutiliza:

- Event Bus atual;
- domain events existentes;
- Workflow events;
- Learning events.

Critério de aceite:

- não cria dependência circular;
- eventos têm testes;
- não força event-driven onde leitura direta é mais simples.

## Fase 17 — Dashboard Do Autopilot OS

Objetivo:

- consolidar operação em um painel de supervisão.

Mostrar:

- canais;
- twins;
- objetivos;
- calendário;
- decisões;
- media strategy;
- creative briefs;
- custos;
- recursos;
- ciclos de aprendizado;
- bloqueios;
- aprovações pendentes.

Reutiliza:

- dashboards existentes;
- componentes Growth;
- API client atual.

Critério de aceite:

- não cria landing page;
- tela é operacional;
- usuário consegue supervisionar tudo sem procurar em 20 telas.

## Fase 18 — Hardening, Pentest E Observabilidade

Objetivo:

- reforçar segurança, confiabilidade e operação.

Cobrir:

- SSRF em fontes externas;
- permissões;
- rate limit;
- OAuth token expiry;
- publicação indevida;
- custos excessivos;
- logs sensíveis;
- isolamento por organização/canal;
- testes de regressão.

Reutiliza:

- Growth Hardening;
- Readiness;
- Gateway hardening;
- API key scopes;
- Billing/quotas;
- Prometheus.

Critério de aceite:

- testes de segurança passam;
- endpoints sensíveis exigem editor/admin;
- modo `dry_run` continua padrão onde houver risco.

## Fase 19 — E2E Autopilot

Objetivo:

- validar fluxo completo de ponta a ponta.

Fluxo:

Canal conectado
→ Channel Twin
→ Objetivo
→ Audience/Market/Trend
→ Calendário
→ Content Decision
→ Media Strategy
→ Creative Brief
→ Workflow
→ Publisher/Scheduler
→ Analytics
→ Learning Temporal
→ Nova decisão

Critério de aceite:

- E2E em modo `dry_run`;
- E2E em modo assistido;
- E2E com falhas simuladas;
- relatório final de prontidão.

## Ordem Recomendada

Execução recomendada:

1. Fase 0 — Contrato Arquitetural.
2. Fase 1 — Pacote Autopilot mínimo.
3. Fase 6 — Media Strategy Engine.
4. Fase 8 — Creative Direction Brief.
5. Fase 4 — Audience Intelligence.
6. Fase 2 — Objective Engine.
7. Fase 3 — Digital Twin.
8. Fase 11 — Closed Learning Temporal.
9. Fase 12 — Prompt Evolution.
10. Fase 9 — Cost Intelligence.
11. Fase 10 — Resource Manager.
12. Fase 5 — Market/Trend avançado.
13. Fase 13 — Community integrada.
14. Fase 14 — Social Autopilot.
15. Fase 15 — Governance multi-canal.
16. Fase 16 — Event Driven Coordination.
17. Fase 17 — Dashboard Autopilot OS.
18. Fase 18 — Hardening/Pentest.
19. Fase 19 — E2E final.

Essa ordem prioriza segurança arquitetural e lacunas de maior impacto antes de expandir para social, governança e dashboard.

## Entrega Obrigatória Por Fase

Cada fase deve entregar:

- arquivos criados;
- arquivos modificados;
- motivação;
- diagrama ou fluxo;
- APIs impactadas;
- modelos reutilizados;
- dependências;
- testes;
- riscos;
- plano de rollback;
- próximos passos.

## Regras De Rollback

- Preferir mudanças aditivas.
- Evitar migrações de banco até a necessidade ser comprovada.
- Não mover código existente só por organização.
- Se criar pacote novo, manter adapters finos.
- Se a fase falhar, desativar por feature flag ou remover apenas arquivos novos.

## Definição Final De Pronto

O ContentOS estará 100% como Autonomous Creator Operating System quando:

- o usuário conectar canais;
- o sistema entender canal, nicho, público, marca, concorrentes e performance;
- o sistema gerar objetivos e calendário;
- o sistema decidir conteúdo, mídia e direção criativa;
- o sistema delegar produção/publicação aos módulos existentes;
- o sistema monitorar resultados;
- o sistema aprender em ciclos temporais;
- o sistema sugerir melhorias de prompts, memória, estratégia e calendário;
- o sistema respeitar custos, recursos, permissões e limites;
- o usuário atuar principalmente como supervisor.

