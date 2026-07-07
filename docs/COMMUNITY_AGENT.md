# Community Agent — V5.4.4

Gera **rascunhos de resposta** a comentários OAuth — **sem publicação automática**.

## Regra de ouro

`COMMUNITY_AUTO_POST` permanece **false** em V5.4.4. Aprovar um rascunho marca status `approved` mas **não publica** na plataforma.

## Fluxo

```
OAuth comments (V5.4.3 fetchers)
        ↓
Prioridade: pergunta > negativo > positivo
        ↓
Rascunho rules-based (question / support / thanks / general)
        ↓
community_reply_drafts (status: draft | approved | dismissed)
```

## API

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/community/drafts/generate` | Gera rascunhos |
| GET | `/api/v1/community/drafts?project_id=` | Lista rascunhos |
| PATCH | `/api/v1/community/drafts/{id}` | `approved` ou `dismissed` |

## Variáveis de ambiente

```env
COMMUNITY_AGENT_ENABLED=true
COMMUNITY_AUTO_POST=false
COMMUNITY_DRAFTS_MAX=20
```

## Dashboard

`/community` — gerar, aprovar ou descartar rascunhos.

## Testes

```powershell
pytest tests/test_community_agent.py -q
```

## Próximo

**V5.5.1** — Command Center (evoluir `/executive`).
