# Content Factory — V5.3

Produção em lote: **N vídeos por tema** com rotação automática de `content_angle` e `hook_hint`, validação de quotas/créditos e aprovação humana opcional antes da publicação.

## Componentes

| ID | Entrega | Local |
|----|---------|--------|
| V5.3.1 | `BatchProductionService` | `intelligence/application/content_factory/service.py` |
| V5.3.2 | Variação hook/ângulo | `variation.py` + `dna_v2.VALID_CONTENT_ANGLES` |
| V5.3.3 | Quotas e custo por lote | `quota_service.assert_can_start_batch`, `estimate_batch_cost` |
| V5.3.4 | Dashboard `/factory` | `apps/dashboard/.../factory/page.tsx` |
| V5.3.5 | Aprovação antes de publicar | `factory_publish_hold` no publisher + `POST .../approve-publish` |

## Fluxo

```
POST /factory/plan          → pré-visualiza variações
POST /factory/batches/estimate → custo N × pipeline_credit_cost
POST /factory/batches       → cria lote (status: planned)
POST /factory/batches/{id}/start → cria N pipelines com context_json
POST /factory/batches/{id}/approve-publish → libera publisher
```

Cada pipeline recebe em `context_json`:

- `content_angle` — sobrescreve DNA no payload do workflow
- `hook_hint` — sugestão de abertura para roteiro
- `factory_batch_id`, `factory_batch_index`
- `factory_publish_hold` / `factory_publish_approved`

O step `publisher` respeita o hold: status `pending_batch_approval` até aprovação do lote.

## API

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/factory/plan` | Plano de variações (sem persistir) |
| POST | `/api/v1/factory/batches/estimate` | Estimativa quota + créditos |
| POST | `/api/v1/factory/batches` | Cria lote (`auto_start` opcional) |
| GET | `/api/v1/factory/batches?project_id=` | Lista lotes |
| GET | `/api/v1/factory/batches/{id}` | Detalhe |
| POST | `/api/v1/factory/batches/{id}/start` | Dispara pipelines |
| POST | `/api/v1/factory/batches/{id}/approve-publish` | Aprova publicação do lote |

## Variáveis de ambiente

```env
CONTENT_FACTORY_ENABLED=true
FACTORY_REQUIRE_APPROVAL=false
FACTORY_MAX_BATCH_SIZE=12
```

## Testes

```powershell
pytest tests/test_content_factory.py -q
```

## Modelo

Tabela `content_batches` (`ContentBatch`) + coluna `pipelines.context_json` para seed do lote.
