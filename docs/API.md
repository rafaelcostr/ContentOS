# ContentOS — Referência de API

OpenAPI interativo:

| Serviço | Docs |
|---------|------|
| API Gateway | http://localhost:8000/docs |
| AI Gateway | http://localhost:8020/docs |

Autenticação: `Authorization: Bearer <access_token>` (exceto health e AI Gateway interno).

---

## Auth

| Method | Path | Descrição |
|--------|------|-----------|
| POST | `/api/v1/auth/register` | Criar conta |
| POST | `/api/v1/auth/login` | Login → tokens |
| GET | `/api/v1/auth/me` | Usuário atual |

---

## Projetos & Pipelines

| Method | Path | Descrição |
|--------|------|-----------|
| GET | `/api/v1/projects` | Listar projetos |
| POST | `/api/v1/projects` | Criar projeto |
| GET | `/api/v1/projects/{id}/pipelines` | Pipelines do projeto (`limit`) |
| POST | `/api/v1/projects/{id}/pipelines` | Criar pipeline `{ topic, workflow_name? }` |
| GET | `/api/v1/pipelines` | Pipelines recentes |
| GET | `/api/v1/pipelines/{id}` | Detalhe + jobs |
| POST | `/api/v1/pipelines/{id}/cancel` | Parar (running/pending) |
| DELETE | `/api/v1/pipelines/{id}` | Excluir (cancela se rodando) |

---

## Workflows

| Method | Path | Descrição |
|--------|------|-----------|
| GET | `/api/v1/workflows` | Templates (`v1-default`, `v2-full`, `v2-dynamic`) |
| GET | `/api/v1/workflows/{name}` | Detalhe do template |

---

## Assets

| Method | Path | Descrição |
|--------|------|-----------|
| GET | `/api/v1/assets` | Listar (`category?`) |
| GET | `/api/v1/assets/search` | Busca avançada (`q`, `category`, `tag`, `theme`, `game`, `character`, `motion`, `color`, `objects`, `limit`) |
| GET | `/api/v1/assets/{id}/preview` | URL assinada MinIO (`expires`) |
| GET | `/api/v1/assets/{id}/content` | Stream autenticado (preview no dashboard) |
| POST | `/api/v1/assets/{id}/tags` | Tags `{ "tags": ["..."] }` |
| GET | `/api/v1/assets/index/stats` | Stats index + storage |
| POST | `/api/v1/assets/takes/upload` | Upload take (multipart) |

---

## IA (via API Gateway)

| Method | Path | Descrição |
|--------|------|-----------|
| GET | `/api/v1/providers/status` | Status configurado |
| GET | `/api/v1/providers/health` | Health Ollama/Piper/Whisper |
| GET | `/api/v1/providers/ai-gateway/health` | Health do AI Gateway |
| GET | `/api/v1/models` | Modelos por agente |
| PATCH | `/api/v1/models/{agent}` | Atualizar provider/model |
| GET | `/api/v1/prompts` | Lista prompts |
| GET/PUT | `/api/v1/prompts/{id}` | Detalhe / editar |

---

## AI Gateway (porta 8020)

| Method | Path | Descrição |
|--------|------|-----------|
| GET | `/health` | Health |
| GET | `/v1/providers` | Providers registrados |
| GET | `/v1/providers/resolve` | Rota por agente (`agent`, `provider_type`) |
| POST | `/v1/text/chat-json` | Chat JSON (`provider`, `system`, `user`, `model?`, `agent?`) |
| POST | `/v1/speech/tts` | TTS → `audio/mpeg` |
| POST | `/v1/subtitle/transcribe` | Transcrição (multipart) |
| POST | `/v1/image/generate` | Imagem → `image/jpeg` |
| POST | `/v1/vision/analyze` | Visão (multipart) |
| POST | `/v1/embeddings` | Embeddings `{ text }` |

---

## Observabilidade

| Method | Path | Descrição |
|--------|------|-----------|
| GET | `/api/v1/agents` | Stats dos agentes |
| GET | `/api/v1/agents/{name}` | Detalhe + logs |
| GET | `/api/v1/analytics/overview` | Overview |
| GET | `/api/v1/analytics/performance` | Por step |
| GET | `/metrics` | Prometheus scrape (Tier E2; token opcional) |
| GET | `/api/v1/metrics/system` | CPU/RAM/GPU |
| GET | `/api/v1/metrics/infrastructure` | Postgres/Redis/Celery |
| GET | `/api/v1/costs/overview` | Custos |
| GET | `/api/v1/events/recent` | Event Bus |
| GET | `/api/v1/cache/stats` | Cache |

---

## Content Sources

| Method | Path | Descrição |
|--------|------|-----------|
| GET | `/api/v1/content-sources` | Sources habilitadas |
| GET | `/api/v1/content-sources/health` | Health |
| GET | `/api/v1/content-sources/collections` | Coleções recentes |

---

## WebSocket

```
ws://localhost:8000/ws
```

Eventos de pipeline em tempo real (`pipeline:created`, `step:completed`, etc.).
