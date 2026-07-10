# Contrato Arquitetural Do Autopilot

Data: 2026-07-10

Este contrato define a fronteira arquitetural do Autopilot no ContentOS.

O Autopilot e uma camada estrategica. Ele observa, aprende, pensa, planeja e delega. Ele nao executa diretamente producao, publicacao, workers, Celery, download de midia, analytics, memoria ou learning.

## Objetivo

Evitar que o Autopilot duplique responsabilidades de modulos maduros do ContentOS.

O Autopilot deve coordenar o sistema como um cerebro decisor:

- coleta contexto por read models e adapters;
- gera decisoes estrategicas;
- gera planos;
- gera policies;
- gera metadata;
- gera recomendacoes;
- delega a execucao para modulos existentes.

## Responsabilidades Permitidas

O Autopilot pode:

- montar contexto estrategico;
- consultar Growth OS;
- consultar Project Memory, Brand DNA e Channel Memory por adapters;
- consultar Analytics e Performance Learning por adapters;
- consultar Knowledge Base por adapters;
- consultar Asset Manager e Content Sources por adapters;
- consultar Scheduler e Publisher apenas como estado/readiness, nunca como executor direto;
- gerar decisoes;
- gerar planos de calendario;
- gerar planos de media;
- gerar briefs criativos;
- gerar recomendacoes;
- gerar eventos de dominio;
- gerar bloqueios e motivos de nao execucao;
- pedir aprovacao humana;
- delegar execucao via servicos de aplicacao existentes.

## Responsabilidades Proibidas

O Autopilot nunca pode:

- importar `celery`;
- importar `contentos_agents`;
- importar handlers de agentes;
- importar `contentos_workflow.tasks`;
- chamar `.delay()` ou `.apply_async()` diretamente;
- publicar em plataforma diretamente;
- baixar midia diretamente;
- renderizar video diretamente;
- criar jobs de worker diretamente;
- escrever credenciais OAuth;
- substituir Scheduler;
- substituir Publisher;
- substituir Analytics;
- substituir Memory;
- substituir Learning;
- substituir Knowledge Base;
- criar memoria paralela.

## Dependencias Permitidas

Permitidas por padrao:

- `contentos_growth` para read models, strategy, calendar, closed loop e managers;
- `contentos_memory` por adapters/read models;
- `contentos_intelligence` por adapters/read models;
- `contentos_database` apenas para modelos e repositorios quando necessario;
- `contentos_events` para eventos de dominio;
- `contentos_shared` para tipos, schemas e utilitarios;
- bibliotecas padrao do Python;
- SQLAlchemy/FastAPI apenas nas camadas corretas, nao no dominio puro.

## Dependencias Restritas

O Autopilot pode ler estado de Scheduler, Publisher, Analytics e Workflow por adapters de aplicacao, mas nao pode executar responsabilidades desses modulos.

Exemplos permitidos:

- perguntar se um item pode ser agendado;
- montar um plano de agendamento;
- ler status de publicacao;
- ler status de pipeline;
- ler health de workers;
- gerar metadata para `context_json`.

Exemplos proibidos:

- chamar Publisher para postar;
- chamar Workflow Engine diretamente de dentro do dominio;
- iniciar Celery;
- criar worker job direto;
- baixar asset externo direto.

## Matriz De Responsabilidade

| Capacidade | Dono Executor | Papel Do Autopilot |
|---|---|---|
| Produzir video | Workflow Engine + agentes | Decide quando e por que produzir |
| Agendar | Scheduler | Decide janela e prioridade |
| Publicar | Publisher | Decide recomendacao e readiness |
| Analytics | Platform Analytics | Consome sinais |
| Learning | Learning Engine | Consome aprendizado e gera proximas decisoes |
| Memoria | Project/Channel/Creative Memory | Consome e sugere atualizacoes |
| Midia | Asset Manager + Content Sources + agentes | Decide estrategia de midia |
| Custo | Billing/Cost/AI Gateway | Decide se vale executar |
| Recursos | Metrics/Workers/Scheduler | Decide se deve esperar |
| Prompts | Prompt Manager | Sugere versoes, nunca sobrescreve |

## Contratos Estrategicos Iniciais

Contratos esperados nas proximas fases:

- `AutopilotContext`
- `AutopilotDecision`
- `AutopilotBrain`
- `ObjectiveTree`
- `ChannelTwinSnapshot`
- `AudienceIntelligenceSnapshot`
- `MediaStrategyPlan`
- `CreativeDirectionBrief`
- `CostDecisionScore`
- `ResourceReadiness`
- `ClosedLoopCyclePolicy`
- `PromptSuggestion`
- `ChannelGovernancePolicy`

Esses nomes representam contratos estrategicos. Eles nao exigem, por si so, tabelas novas, endpoints novos ou pacotes novos.

## Regras Para Novos Dominios

Antes de criar qualquer novo pacote, tabela, endpoint ou servico:

1. Procurar modulo equivalente.
2. Preferir contrato/read model.
3. Preferir adapter.
4. Preferir policy.
5. Preferir metadata em entidade existente.
6. Criar pacote novo apenas se a fronteira arquitetural justificar.

## Regras Para Eventos

Eventos sao preferenciais para comunicacao assincrona e desacoplada.

Chamadas diretas sao permitidas para:

- leitura;
- composicao de read models;
- servicos de aplicacao existentes;
- endpoints que apenas agregam dados.

Eventos nao devem ser usados para complicar fluxos simples de leitura.

## Testes Arquiteturais

O projeto deve manter testes garantindo que os modulos de Autopilot:

- nao importam Celery;
- nao importam Worker;
- nao importam agentes;
- nao importam `contentos_workflow.tasks`;
- nao chamam `.delay()` ou `.apply_async()`;
- nao publicam diretamente;
- nao duplicam Scheduler, Publisher, Analytics, Memory, Learning ou Knowledge Base.

## Rollback

Como a Fase 0 e documental e de testes:

- rollback seguro: remover este documento e `tests/test_autopilot_architecture.py`;
- nenhum banco e alterado;
- nenhum endpoint e alterado;
- nenhuma feature runtime e criada.

