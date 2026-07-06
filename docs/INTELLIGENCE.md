# ContentOS V4 — Intelligence Package

| Campo | Valor |
|-------|--------|
| **Pacote** | `packages/intelligence` (`contentos-intelligence`) |
| **Fase** | V4.0.1 |
| **Roadmap** | [V4_ROADMAP.md](./V4_ROADMAP.md) |
| **Consolidação** | [V4_CONSOLIDATION_MAP.md](./V4_CONSOLIDATION_MAP.md) |

---

## Objetivo

Pacote único de **contratos** e **injeção de dependência** para todos os epics V4. Módulos não importam implementações uns dos outros — apenas interfaces registradas em `IntelligenceRegistry`.

---

## Estrutura

```
packages/intelligence/src/contentos_intelligence/
├── domain/
│   ├── interfaces.py          # IViralityScorer, IKnowledgeQuery, ...
│   ├── context.py             # IntelligenceContext
│   ├── viral_report.py
│   ├── reuse_suggestion.py
│   ├── content_score.py
│   ├── knowledge.py
│   ├── specialist.py
│   └── ab_testing.py
├── application/
│   ├── registry.py            # IntelligenceRegistry (DI)
│   ├── content_intelligence_service.py
│   ├── viral_engine.py
│   ├── ab_testing/            # Epic 6 — generators, scoring, service
│   ├── content_score/         # Epic 9 — dimensions, service
│   ├── specialists/           # Epic 5 — catalog, selector
│   ├── multi_content/         # Epic 2a — text generators
│   ├── multi_content_video/   # Epic 2b — platform variants
│   ├── learning/              # Epic 7 — post-pipeline learning
│   ├── trend_forecast/        # Epic 10 — score + growth
│   ├── content_graph/         # Epic 11 — relation graph
│   ├── executive/           # Epic 12 — dashboard summary
│   └── noop.py                # stubs até epics implementarem
├── infrastructure/
│   ├── ab_repository.py
│   ├── multi_content_repository.py
│   ├── video_variants_repository.py
│   ├── learning_repository.py
│   ├── trend_forecast_repository.py
│   └── content_graph_repository.py
```

---

## Interfaces

| Interface | Epic | Responsabilidade |
|-----------|------|------------------|
| `IViralityScorer` | 1 | Score viral + recomendações |
| `IKnowledgeQuery` | 3 | Busca semântica na KB |
| `IReuseAdvisor` | 4 | Sugestões de reuso (`ReuseAdvisor`) |
| `IContentScorer` | 9 | Nota 0–100 agregada |
| `ISpecialistSelector` | 5 | Escolha de especialista |
| `IViralEngine` | 1 | Orquestra analisadores |
| `IContentIntelligenceService` | 1+4 | Step composto `content_intelligence` |
| `IEmbeddingClient` | 3 | Vetores via AI Gateway |

---

## Uso

```python
from uuid import uuid4
from contentos_intelligence import IntelligenceContext, get_intelligence_registry

registry = get_intelligence_registry()
context = IntelligenceContext(
    project_id=uuid4(),
    pipeline_id=uuid4(),
    topic="IA no marketing",
    payload={"emotion": {"retention": 7.5}},
)

service = registry.content_intelligence_service()
result = await service.run(context)
# result["viral_report"], result["reuse_suggestions"]
```

### Registrar implementação customizada

```python
registry = get_intelligence_registry()
registry.register_virality_scorer(MyViralScorer())
```

---

## NoOp defaults

Até os epics V4.0.2+ entregarem implementações reais, o registry usa `NoOp*` que retornam estruturas vazias sem falhar. Isso permite importar o pacote em `agents-worker` e `gateway` sem quebrar pipelines V1/V2/V3.

---

## Integração futura

| Consumidor | Quando |
|------------|--------|
| `handlers/content_intelligence.py` | V4.0.5 |
| `apps/backend` routes `/viral`, `/knowledge` | V4.0.3+ |
| Epic 3 `EmbeddingIndex` | registra `IEmbeddingClient` real |

---

## Testes

```bash
pytest tests/test_intelligence.py -v
```
