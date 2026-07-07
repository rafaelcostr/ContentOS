# ContentOS - Mapa da Linha de Montagem

Este documento organiza o ContentOS por módulos de manutenção e mostra como a linha de montagem completa se conecta ao código atual.

A fonte executável da ordem da fábrica é `PipelineStep.factory_full_ordered()`.
A fonte descritiva para produto, dashboard e documentação é `packages/shared/src/contentos_shared/factory_map.py`.
A tabela técnica única (handler, fila, evento, dependência) está em [`docs/FACTORY_TRUTH_TABLE.md`](FACTORY_TRUTH_TABLE.md).

## Resumo Oficial

- Workflow: `factory-full`
- Etapas executáveis: 31
- Entradas de produto: projeto e tema
- Acompanhamento operacional: dashboard
- Total exibido neste mapa: 34 itens, sendo 31 steps executáveis

## Módulos

| Módulo | Responsabilidade |
|---|---|
| Projeto e briefing | Projeto, tema, nicho, organização e workflow escolhido |
| Criação criativa | Pesquisa, gancho, roteiro, revisão, cenas, storyboard e direção |
| Assets e biblioteca | Fontes autorizadas, coleta, análise, indexação, tags, busca e takes |
| Produção audiovisual | Voz, legendas, FFmpeg, renderização e thumbnail |
| Qualidade e retry | Validação técnica, retenção, revisão criativa, content score e auto retry |
| Inteligência e memória | Trend, viral, learning, knowledge base, creative memory e analytics |
| Publicação | SEO, metadados, OAuth, plugins e publicação |
| Dashboard | Status, filas, custos, métricas e operação em tempo real |

## Linha de Montagem

| Ordem | Etapa | Módulo | Estado | Step executável | Implementação atual |
|---:|---|---|---|---|---|
| 1 | Criar projeto | Projeto | Pronto | - | API de projetos |
| 2 | Informar tema | Projeto | Pronto | - | Criação de pipeline |
| 3 | Research Agent | Criação | Pronto | `research` | Research handler |
| 4 | Trend Intelligence | Inteligência | Pronto | `trend_intelligence` | Trend handler |
| 5 | Hook Generator | Criação | Pronto | `hook` | Hook handler |
| 6 | Script Agent | Criação | Pronto | `script` | Script handler |
| 7 | Script Reviewer | Criação | Pronto | `script_review` | Script review handler |
| 8 | Scene Planner | Criação | Pronto | `scene` | Scene handler |
| 9 | Storyboard AI | Criação | Pronto | `storyboard` | Storyboard handler |
| 10 | Scene Director | Criação | Pronto | `scene_director` | Scene director handler |
| 11 | Clip Research | Assets | Parcial | `clip_research` | Descoberta de termos e necessidades de mídia |
| 12 | Asset Collector | Assets | Parcial | `asset_collector` | Fontes autorizadas, download permitido e deduplicação |
| 13 | Asset Manager | Assets | Pronto | `asset_index` | Storage, tags e índice |
| 14 | Media Analyze | Assets | Pronto | `media_analyze` | Media profiles, visão e metadados técnicos |
| 15 | Asset Search | Assets | Pronto | `asset_search` | Busca/ranking semântico de assets |
| 16 | Takes Manager | Assets | Pronto | `takes` | Seleção dos melhores takes |
| 17 | Voice Agent | Produção | Pronto | `voice` | Narração |
| 18 | Subtitle Agent | Produção | Pronto | `subtitle` | Legendas |
| 19 | Editor AI | Produção | Pronto | `editor` | FFmpeg, cortes, efeitos e render |
| 20 | Thumbnail AI | Produção | Parcial | `thumbnail` | Thumbnail handler |
| 21 | Quality AI | Qualidade | Pronto | `quality` | QA técnico |
| 22 | Retention Engine | Qualidade | Pronto | `retention` | Análise segundo a segundo e plano de retry |
| 23 | Video Reviewer | Qualidade | Pronto | `video_review` | Revisão criativa simulada |
| 24 | Auto Retry | Qualidade | Pronto | `auto_retry` | Retry com política no workflow engine |
| 25 | Content Score | Qualidade | Pronto | `content_score` | Nota geral do conteúdo |
| 26 | AI Director | Qualidade | Pronto | `ai_director` | Plano de correção parcial |
| 27 | Viral Intelligence | Inteligência | Pronto | `content_intelligence` | Potencial viral e recomendações |
| 28 | Learning Engine | Inteligência | Pronto | `learning` | Aprendizado do resultado |
| 29 | Knowledge Base | Inteligência | Pronto | `knowledge_base` | Indexação de conhecimento |
| 30 | Creative Memory | Inteligência | Pronto | `creative_memory` | Contexto criativo consolidado |
| 31 | Analytics | Inteligência | Pronto | `analytics` | Métricas e relatórios |
| 32 | SEO Engine | Publicação | Pronto | `seo` | Metadados por plataforma |
| 33 | Publisher | Publicação | Parcial | `publisher` | Dry-run, plugins, OAuth e publicação |
| 34 | Dashboard | Dashboard | Pronto | - | `apps/dashboard` |

## Ordem Executável do `factory-full`

```text
research -> trend_intelligence -> hook -> script -> script_review -> scene -> storyboard -> scene_director -> clip_research -> asset_collector -> asset_index -> media_analyze -> asset_search -> takes -> voice -> subtitle -> editor -> thumbnail -> quality -> retention -> video_review -> auto_retry -> content_score -> ai_director -> content_intelligence -> learning -> knowledge_base -> creative_memory -> analytics -> seo -> publisher
```

## Estados

- `ready`: existe e pode participar do fluxo atual.
- `partial`: existe, mas precisa de integração real, credenciais, persistência, cobertura ou validação melhor para produção.
- `planned`: ainda precisa virar etapa executável ou política de orquestração.

## Pontos Parciais Atuais

| Etapa | Motivo |
|---|---|
| `clip_research` | Depende de qualidade das fontes, termos e regras de mídia por nicho |
| `asset_collector` | Depende de chaves, limites, licenças e disponibilidade de mídia suficiente |
| `thumbnail` | Precisa validação visual e política de qualidade mais forte |
| `publisher` | Dry-run por padrão; publicação real depende de OAuth, escopos e upload final por plataforma |

## Contratos de Manutenção

- `tests/test_factory_map.py` garante que o mapa descritivo tenha as mesmas 31 etapas de `PipelineStep.factory_full_ordered()`.
- `tests/test_factory_truth_table.py` + [`FACTORY_TRUTH_TABLE.md`](FACTORY_TRUTH_TABLE.md) cobrem handler, fila, evento e dependência externa.
- O dashboard deve exibir `factory-full` como linha de montagem de 31 steps.
- Novas etapas devem ser incluídas em `PipelineStep`, `factory_map.py`, handlers, filas, eventos e testes antes de aparecerem na UI.

## Próximas Fases

1. Manter README, docs e dashboard sincronizados com este mapa.
2. Criar testes de contrato para entrada e saída de cada etapa.
3. Validar E2E real com mídia, voz, render, QA e publisher em modo controlado.
