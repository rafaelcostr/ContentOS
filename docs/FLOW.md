# ContentOS — Fluxo do Pipeline

## Regra de ouro

```
Dashboard → API Gateway → Workflow Engine → Redis/Celery → Agente
Agente → callback HTTP → Workflow Engine → DB + Event Bus → Dashboard
```

**Proibido:** Agente A → Agente B (direto).

---

## Sequência (V2 Dynamic)

```mermaid
sequenceDiagram
    participant U as Usuário
    participant D as Dashboard
    participant G as API Gateway
    participant W as Workflow Engine
    participant Q as Redis/Celery
    participant A as Agente
    participant AI as AI Gateway
    participant CS as Content Sources
    participant S as Asset Manager
    participant EB as Event Bus
    participant DB as PostgreSQL

    U->>D: Tema "GTA 6" (workflow v2-dynamic)
    D->>G: POST /projects/{id}/pipelines
    G->>W: create_pipeline(topic, workflow)
    W->>DB: INSERT pipeline + jobs
    W->>Q: enqueue(research)
    W-->>EB: pipeline.created
    EB-->>D: WS update

    Q->>A: execute(research)
    A->>AI: chat-json (agent=research)
    A->>W: callback(result)
    W->>EB: research.finished
    W->>Q: enqueue(next)

    Note over W,Q: script → scene → clip_research → asset_collector → asset_index → media_analyze → asset_search

    Q->>A: execute(clip_research)
    A->>CS: search candidates
    A->>W: callback(scene_candidates)

    Q->>A: execute(asset_collector)
    A->>CS: fetch files
    A->>S: store_and_persist (MinIO + PG)
    A->>W: callback(assets)

    Note over W,Q: takes → voice → subtitle → editor → quality → publisher → thumbnail → analytics

    Q->>A: execute(publisher)
    A->>W: callback(result)
    W->>DB: pipeline COMPLETED
    W-->>EB: pipeline.completed
    EB-->>D: WS pipeline:completed
```

---

## Templates

| Template | Steps | Uso |
|----------|-------|-----|
| `v1-default` | 9 | Pipeline clássico (compat) |
| `v2-full` | 9 + async | V1 + clip/thumbnail/analytics async |
| `v2-dynamic` | 16 | Pipeline completo da missão |

```env
DEFAULT_WORKFLOW=v1-default
# ou v2-dynamic para produção completa
```

---

## Pipeline V1 (9 steps)

```
research → script → scene → takes → voice → subtitle → editor → quality → publisher
```

## Pipeline V2 Dynamic (16 steps)

```
research
  ↓
script
  ↓
scene
  ↓
clip_research      ← Content Sources (candidatos, sem download)
  ↓
asset_collector    ← fetch + MinIO + PostgreSQL (AssetPipelineService)
  ↓
asset_index        ← tags / indexação
  ↓
media_analyze      ← análise IA, perfis de mídia e metadados técnicos
  ↓
asset_search       ← busca os melhores assets indexados por cena
  ↓
takes              ← só seleção (não pesquisa mídia)
  ↓
voice
  ↓
subtitle
  ↓
editor             ← 1080x1920 @ 60fps H264
  ↓
quality            ← validação + retry editor
  ↓
publisher          ← dry_run por padrão
  ↓
thumbnail          ← ImageProvider via AI Gateway
  ↓
analytics          ← Analytics AI
```

Dashboard: **Produção** (`/jobs`) e **Orquestração** (`/workflow`).

---

## Retry & DLQ

```mermaid
flowchart LR
    RUN[Job Running] -->|success| OK[Completed]
    RUN -->|error| RET{Retries < 3?}
    RET -->|yes| WAIT[Backoff 30s/60s/120s]
    WAIT --> RUN
    RET -->|no| DLQ[Dead Letter Queue]
    DLQ --> MAN[Reprocessamento Manual]
```

## Quality — loop de correção

Se Quality falhar, o Workflow reenvia **apenas o step com erro**:

| Falha | Reenvia para |
|-------|-------------|
| Áudio ausente | voice |
| Legenda ausente | subtitle |
| Resolução incorreta | editor |
| Arquivo corrompido | step que gerou o asset |

---

## Cancelar / Excluir

| Ação | API | Dashboard |
|------|-----|-----------|
| Parar | `POST /api/v1/pipelines/{id}/cancel` | Produção → **Parar** |
| Excluir | `DELETE /api/v1/pipelines/{id}` | Produção → **Excluir** |

Cancelamento marca jobs como `cancelled` e revoga tasks Celery.



