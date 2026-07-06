# ContentOS V4 — Mapa de Consolidação V3 → V4

| Campo | Valor |
|-------|--------|
| **Objetivo** | Evitar duplicação; cada Epic V4 estende ou compõe módulos V3 |
| **Roadmap** | [V4_ROADMAP.md](./V4_ROADMAP.md) |
| **ADR** | [ADR-008](./ADR.md#adr-008--v4-inteligência-aditiva-e-pacote-único) |

**Legenda**

| Ação | Significado |
|------|-------------|
| **EXTEND** | Adicionar campos, métodos ou handlers ao módulo existente |
| **COMPOSE** | Novo serviço que agrega outputs de módulos V3 (fachada) |
| **NEW** | Código genuinamente novo, sem paralelo V3 |
| **UI ONLY** | Dashboard/API em cima de dados já existentes |

---

## Visão geral dos 12 Epics

| Epic | Nome | Ação principal | Módulo V3 base | Pacote V4 alvo |
|------|------|----------------|----------------|----------------|
| 1 | Viral Intelligence | COMPOSE | hook, emotion, trend_intelligence, quality | `intelligence/viral/` |
| 2 | Multi Content Engine | NEW | script, publisher, prompts | `intelligence/content/` |
| 3 | Knowledge Base | EXTEND | storage, database, ai-gateway embeddings | `intelligence/knowledge/` |
| 4 | Smart Reuse Engine | NEW (usa KB) | memory, asset index | `intelligence/reuse/` |
| 5 | Specialist Agents | EXTEND | agent_catalog, prompts, models | `intelligence/specialists/` |
| 6 | A/B Testing | EXTEND | hook, thumbnail | `intelligence/ab_testing/` |
| 7 | Learning Engine | EXTEND | analytics-ai, memory, events | `intelligence/learning/` |
| 8 | Project DNA | EXTEND | ProjectMemory, memory_service | `memory/` (+ DNA fields) |
| 9 | Content Score | COMPOSE | quality_scoring, video_review, viral | `intelligence/scoring/` |
| 10 | Trend Forecast | EXTEND | trend_intelligence | `intelligence/trend/` |
| 11 | Content Relation Graph | NEW | domain_events, KB | `intelligence/graph/` |
| 12 | Executive Dashboard | UI ONLY | dashboard Next.js | `apps/dashboard/` |

---

## Epic 1 — Viral Intelligence Engine

### O que o prompt V4 pede

`ViralEngine`, `RetentionPredictor`, `ViralityScore`, `TrendMatcher`, `HookAnalyzer`, `SceneAnalyzer`, `RhythmAnalyzer`, `EmotionPredictor` → relatório `viral_report`.

### O que já existe (V3)

| Componente V3 | Path | Output atual |
|---------------|------|--------------|
| Hook Generator | `handlers/hook.py` | `selected_hook`, candidatos | 
| Emotion Analyzer | `handlers/emotion.py` | scores emoção/curiosidade/retenção |
| Trend Intelligence | `handlers/trend_intelligence.py` | `trend_context` |
| Quality (técnico) | `quality_scoring.py` | `quality_score` 0–10 |
| Video Review (criativo) | `handlers/video_review.py` | `video_score` 0–10 |

### Decisão de consolidação

| Classe V4 | Implementação | Fonte |
|-----------|---------------|-------|
| `HookAnalyzer` | LLM + regras sobre payload `hook` | EXTEND hook agent output |
| `EmotionPredictor` | Adapter sobre `emotion` step | COMPOSE |
| `RhythmAnalyzer` | Heurísticas + `director_plan` / scene timing | NEW (dados já no payload) |
| `SceneAnalyzer` | Adapter sobre `storyboard` + `scenes` | COMPOSE |
| `TrendMatcher` | Adapter sobre `trend_context` | COMPOSE |
| `RetentionPredictor` | Modelo heurístico/LLM agregando acima | NEW |
| `ViralityScore` | Ponderação dos analisadores | NEW |
| `ViralEngine` | Orquestrador DI do step `content_intelligence` | NEW |

**Não criar:** segundo hook agent, segundo emotion agent, segundo trend step no pipeline default.

---

## Epic 2 — Multi Content Engine

### O que já existe

| Componente | Path |
|------------|------|
| Script model | `database/models.py` → `Script` |
| Publisher | `handlers/publisher.py` (YouTube, TikTok, Instagram OAuth) |
| Prompt Manager | `packages/prompts/` |

### Decisão

| Gerador V4 | Ação | Prompt novo |
|------------|------|-------------|
| `ArticleGenerator` / `SeoGenerator` | NEW | `prompts/seo_article.md` |
| `ThreadGenerator` | NEW | `prompts/thread_x.md` |
| `NewsletterGenerator` | NEW | `prompts/newsletter.md` |
| `LinkedinGenerator` | NEW | `prompts/linkedin_post.md` |
| `CarouselGenerator` | NEW | `prompts/instagram_carousel.md` |
| `PodcastGenerator` | NEW | `prompts/podcast_script.md` |
| TikTok / Shorts / Reels | EXTEND publisher metadata | flags em `Video` + crop specs |

**ContentGenerator** = fachada que recebe `script_id` e dispara N geradores (Celery group ou step opcional pós-`publisher`).

---

## Epic 3 — Knowledge Base

### O que já existe

| Componente | Path | Gap |
|------------|------|-----|
| Asset Index | `storage/.../asset_index_service.py` | Sem embeddings |
| Script persistence | `Script` model | Sem version history dedicado |
| Analytics insights | `AnalyticsInsight` | Por pipeline, não indexado semanticamente |
| Embeddings API | `ai-gateway/.../embedding.py` | Existe, pouco usado |
| Project memory history | `ProjectMemory.history` | Lista simples, não searchable |

### Decisão

| Classe V4 | Ação | Storage |
|-----------|------|---------|
| `KnowledgeBase` | NEW service | PG + opcional pgvector |
| `EmbeddingIndex` | NEW | Chama AI Gateway; cache em PG |
| `SemanticSearch` | NEW | Query embeddings + filtros org/project |
| `ContentHistory` | EXTEND | Agrega Script, Video, hooks de jobs |
| `VersionHistory` | EXTEND | `Asset.version` chain + script revisions |

**Não criar:** segundo Asset Manager ou segundo banco de assets.

---

## Epic 4 — Smart Reuse Engine

### Dependências

- Epic 3 (KB) — busca por similaridade
- Epic 8 (DNA) — contexto de projeto

### Componentes

| Classe | Ação |
|--------|------|
| `ReuseAdvisor` | NEW — consulta KB antes de `hook`/`script` |
| Interfaces | `IReuseAdvisor.suggest(script_topic) → ReuseSuggestion[]` |

Integração: chamado **dentro** de `content_intelligence` ou como pré-step leve (mesmo handler).

---

## Epic 5 — Specialist Agents

### O que já existe

| Componente | Path |
|------------|------|
| Agent catalog | `shared/agent_catalog.py` |
| Prompt overrides | `prompt_service.py` |
| Model per agent | `AgentModelSetting` |

### Decisão

| Classe V4 | Ação |
|-----------|------|
| `AgentRegistry` | EXTEND `agent_catalog` com metadata specialist |
| `SpecialistManager` | NEW — CRUD specialists (prompt pack + vocabulary) |
| `AgentSelector` | NEW — Workflow Engine escolhe por `project.niche` ou DNA |

**Piloto V4.1:** Gaming, Technology, Business — validar selector antes dos outros 8.

**Não criar:** agents-worker separados por nicho; mesmo handler, prompt/specialist injetado.

---

## Epic 6 — Automatic A/B Testing

### O que já existe

- `hook` gera candidatos (parcial)
- `thumbnail` gera imagem

### Decisão

| Variante | Ação |
|----------|------|
| 3 Hooks | EXTEND hook handler ou sub-step em `content_intelligence` |
| 3 Títulos | NEW campo em payload + persistência |
| 3 CTAs | EXTEND script / DNA |
| 3 Thumbnails | EXTEND thumbnail (3 tasks) |
| 3 Openers | NEW (primeiros N segundos de script/takes) |
| Seleção automática | `ViralityScore` ou `ContentScore` pré-render |

Persistência: tabela `ab_variants` (pipeline_id, dimension, variants JSON, winner).

---

## Epic 7 — Learning Engine

### O que já existe

| Componente | Path |
|------------|------|
| Analytics AI | `analytics_service.py` — insights pós-pipeline |
| Memory apply | `applied_to_memory` em insights |
| Event Bus | `pipeline.completed`, step events |

### Decisão

| Classe V4 | Ação |
|-----------|------|
| `LearningEngine` | NEW — consumer de `pipeline.completed` |
| Atualiza | Memory (EXTEND), KB (Epic 3), Analytics (EXTEND) |

**Limitação documentada:** sem métricas externas (views TikTok), learning é **interno** (scores, prompts, variants). Integração OAuth analytics = fase futura.

---

## Epic 8 — Project DNA

### O que já existe — `ProjectMemoryData`

```
tone, vocabulary, cta, avg_duration, hook_style, niche, goal, style{}, history[]
```

### Campos DNA novos (EXTEND)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `humor_level` | float 0–1 | Intensidade de humor |
| `pace` | enum | slow \| medium \| fast |
| `visual_style` | dict | cores, tipografia, mood |
| `narrator_persona` | str | Voz/persona TTS |
| `preferred_formats` | list[str] | shorts, reels, article, … |
| `hook_patterns` | list[str] | Padrões favoritos |
| `cta_style` | str | urgência, suave, pergunta |

**Não criar** tabela `project_dna` separada — estender `project_memory` (migration aditiva, JSON columns).

`format_context()` ganha seção DNA automática para `{{memory_context}}`.

---

## Epic 9 — Content Score

### Fontes existentes

| Fonte | Escala | Path |
|-------|--------|------|
| `quality_score` | 0–10 | `quality_scoring.py` |
| `video_score` | 0–10 | `video_review.py` |
| Emotion scores | 0–10 cada | `emotion.py` payload |

### Decisão

`ContentScoreService` = **COMPOSE** — normaliza tudo para 0–100, pesos configuráveis por org.

**Não substituir** quality nem video_review; apenas agregar relatório `content_score_report`.

---

## Epic 10 — Trend Forecast

### O que já existe

`trend_intelligence.py` — agrega memory + analytics → patterns para research.

### Decisão

| Output novo | Ação |
|-------------|------|
| `trend_score` | EXTEND handler |
| `expected_growth` | NEW heurística + histórico KB |
| `production_recommendation` | NEW string no payload |

Evitar segundo step; evoluir agent existente ou sub-módulo chamado por `content_intelligence`.

---

## Epic 11 — Content Relation Graph

### Fontes de arestas

| Nó | Tabela/Evento |
|----|---------------|
| Video | `videos` |
| Script | `scripts` |
| Asset | `assets` |
| Specialist | registry V4 |
| Prompt version | `prompt_service` |
| Pipeline job outputs | `jobs.output` |

### Decisão

- **NEW** `content_graph` — adjacency em PG (ou tabela `content_relations`)
- Populado por Learning Engine + indexação KB
- Query API: `GET /graph/neighbors?node_id=&type=`

---

## Epic 12 — Executive Dashboard

### Páginas → API V4

| Página | API base |
|--------|----------|
| Viral Intelligence | `/viral/*`, payload jobs |
| Knowledge Base | `/knowledge/*` |
| DNA | `/projects/{id}/dna` |
| Content Score | `/content-score/{pipeline_id}` |
| A/B Tests | `/ab-variants/*` |
| Trend Forecast | trend payload + `/trend/forecast` |
| Specialists | `/specialists/*` |
| Learning | `/learning/insights` |
| Reuse | `/reuse/suggest` |
| Graph | `/graph/*` |

**UI ONLY** após APIs estáveis — não antecipar mockups sem backend.

---

## Pacote único: `packages/intelligence/`

Estrutura alvo (Epic V4.0.1):

```
packages/intelligence/
├── pyproject.toml
└── src/contentos_intelligence/
    ├── domain/
    │   ├── interfaces.py      # IViralityScorer, IKnowledgeQuery, ...
    │   ├── viral_report.py
    │   ├── reuse_suggestion.py
    │   └── content_score.py
    ├── application/
    │   ├── viral_engine.py
    │   ├── reuse_advisor.py
    │   ├── content_score_service.py
    │   └── specialist_selector.py
    └── infrastructure/
        ├── kb_repository.py
        └── embedding_client.py   # via ai-client → gateway
```

**Regra:** `agents-worker` importa interfaces; implementações registradas via factory no handler `content_intelligence`.

---

## Step e eventos novos

### PipelineStep (aditivo)

```python
CONTENT_INTELLIGENCE = "content_intelligence"  # tier v4
```

### Template

`v4-intelligence` = insert `content_intelligence` após `emotion` em `V3_QUALITY_STEPS`.

### Eventos (Event Bus)

| Evento | Quando |
|--------|--------|
| `content_intelligence.started` | Início do step |
| `content_intelligence.completed` | `viral_report` no payload |
| `reuse.suggested` | Reuse encontrou match |
| `ab.variant.selected` | Winner escolhido |
| `learning.recorded` | Pós-pipeline learning |
| `knowledge.indexed` | Item indexado na KB |

Aliases PascalCase documentados em `EVENT_BUS.md` (ADR-003).

---

## Matriz de risco de duplicação

| Risco | Mitigação |
|-------|-----------|
| 4 sistemas de score | Epic 9 como única fachada 0–100 |
| 2 memory systems | Epic 8 estende `ProjectMemory` |
| 2 trend engines | Epic 10 estende B9 |
| Pipeline com 25+ steps | Step composto `content_intelligence` |
| 11 specialist workers | Prompt injection, mesmo worker |
| KB vs Asset Index | KB indexa **referências**; assets continuam no Asset Manager |

---

## Checklist antes de cada Epic

- [ ] Linha neste mapa revisada (EXTEND vs NEW)
- [ ] Impacto em V1/V2/V3 templates (deve ser zero para defaults)
- [ ] ADR incrementado se decisão estrutural
- [ ] Testes de não-regressão `v1-default`, `v2-dynamic`, `v3-quality`
- [ ] Cost/quota para novas chamadas LLM
