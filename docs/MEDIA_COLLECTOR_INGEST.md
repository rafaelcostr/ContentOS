# Media Collector → ContentOS — Contrato de Ingestão

O Media Collector é o único responsável por **baixar** mídia externa.
O ContentOS só **recebe, indexa e usa** na produção.

## Endpoint canônico

```http
POST /api/v1/assets/takes/upload
```

| Item | Valor |
|------|--------|
| Base URL (local) | `http://localhost:8000` |
| Content-Type | `multipart/form-data` |
| Auth | JWT **ou** API Key org-scoped |
| Role mínima | `editor` (API Key com `scope=write`) |
| Sucesso | `201 Created` |
| Dedup | SHA-256 — mesmo arquivo retorna o asset existente |

---

## Autenticação (escolha uma)

### Opção A — API Key (recomendado para Media Collector)

```http
X-API-Key: cos_{prefix}_{secret}
X-Organization-Id: {uuid-da-org}   # opcional se a key já amarra a org
```

- Criar em: Dashboard → Settings → API Keys, ou `POST /api/v1/organizations/{org_id}/api-keys`
- Body: `{ "name": "media-collector", "scope": "write" }`
- A raw key (`cos_...`) aparece **uma vez** na criação.

### Opção B — JWT de usuário

```http
Authorization: Bearer {access_token}
X-Organization-Id: {uuid-da-org}
```

Login: `POST /api/v1/auth/login` → `access_token`.

---

## Request (multipart)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `theme` | string | **sim** | Tema/nicho (ex.: `GTA 6`, `carros`). Vira tag + facet `game`. |
| `label` | string | **sim** | Rótulo da cena/clip (ex.: `beach`, `chase`, `scene_0`). Usado pelo `takes`. |
| `file` | binary | **sim** | Arquivo de vídeo (preferência `.mp4`). |
| `project_id` | UUID string | não | Liga o asset ao projeto. **Recomendado** para `own_library`. |

### Exemplo cURL

```bash
curl -X POST "http://localhost:8000/api/v1/assets/takes/upload" \
  -H "X-API-Key: cos_SEU_PREFIX_SEU_SECRET" \
  -H "X-Organization-Id: 00000000-0000-0000-0000-000000000001" \
  -F "theme=GTA 6" \
  -F "label=beach" \
  -F "project_id=11111111-1111-1111-1111-111111111111" \
  -F "file=@./clips/gta_beach.mp4;type=video/mp4"
```

### Exemplo Python

```python
import httpx

GATEWAY = "http://localhost:8000"
API_KEY = "cos_...."
ORG_ID = "...."
PROJECT_ID = "...."

def upload_take(path: str, *, theme: str, label: str, project_id: str | None = None) -> dict:
    headers = {
        "X-API-Key": API_KEY,
        "X-Organization-Id": ORG_ID,
    }
    data = {"theme": theme, "label": label}
    if project_id:
        data["project_id"] = project_id
    with path.open("rb") as f:
        files = {"file": (path.name, f, "video/mp4")}
        r = httpx.post(
            f"{GATEWAY}/api/v1/assets/takes/upload",
            headers=headers,
            data=data,
            files=files,
            timeout=120.0,
        )
    r.raise_for_status()
    return r.json()
```

---

## Response `201`

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "category": "takes",
  "object_key": "takes/3f8a9c1b2d4e.mp4",
  "content_type": "video/mp4",
  "size_bytes": 4821930,
  "sha256": "hex64...",
  "tags": ["GTA 6", "beach", "..."],
  "version": 1,
  "metadata_": {
    "theme": "GTA 6",
    "label": "beach",
    "game": "GTA 6"
  },
  "created_at": "2026-07-10T23:00:00.000000Z"
}
```

| Campo | Uso no ContentOS |
|-------|------------------|
| `id` | UUID do asset (Postgres) |
| `object_key` | Path no MinIO (`takes/{12hex}.mp4`) |
| `sha256` | Deduplicação |
| `tags` / `metadata_` | `asset_search` + `takes` matching |

---

## Erros comuns

| HTTP | Causa |
|------|--------|
| `401` | Sem auth / key inválida |
| `403` | API Key `scope=read` (precisa `write`) |
| `422` | Faltou `theme`, `label` ou `file` |
| `429` | Rate limit da API Key (default 120/min) |
| `5xx` | MinIO/Postgres indisponível |

---

## Como o ContentOS usa depois

```
Media Collector
  └─ POST /assets/takes/upload  (theme + label + file + project_id)
        ↓
   MinIO takes/ + row assets
        ↓
   Pipeline: scene → asset_index → media_analyze → asset_search → takes → editor
```

### Convenções de `label` (importante)

O agente `takes` casa cenas por **label**. Alinhe com o Scene Planner:

| Scene `label` | Upload `label` |
|---------------|----------------|
| `beach` | `beach` |
| `chase` | `chase` |
| `scene_0` | `scene_0` |

`theme` deve bater com o `topic` do pipeline quando possível (ex.: ambos `GTA 6`).

### Dedup

Se o mesmo bytes já existir (`sha256`), a API devolve o asset antigo (`201` com o mesmo `id`) — não regrava no MinIO como novo conteúdo lógico.

---

## Checklist Media Collector

1. [ ] Criar API Key `scope=write` na org
2. [ ] Guardar `GATEWAY_URL`, `X-API-Key`, `org_id`, `project_id`
3. [ ] Baixar vídeo (sua lógica)
4. [ ] Upload com `theme` + `label` + `file` + `project_id`
5. [ ] Guardar `id` / `object_key` / `sha256` no seu banco (opcional)
6. [ ] Disparar pipeline no ContentOS só depois da biblioteca ter cobertura suficiente

## O que NÃO fazer

- Não chamar Pexels/Pixabay pelo ContentOS (removido)
- Não gravar direto no MinIO sem row em `assets` (quebra `own_library` / semantic search)
- Não omitir `project_id` se o projeto usa `own_library`
- Não usar labels aleatórios sem relação com as cenas

## APIs auxiliares (opcional)

| Método | Path | Uso |
|--------|------|-----|
| `GET` | `/api/v1/content-sources/health` | Saúde `local_library` / `own_library` |
| `GET` | `/api/v1/assets/search?theme=GTA%206` | Listar takes por tema |
| `GET` | `/api/v1/assets/index/stats` | Contagem da biblioteca |
| `POST` | `/api/v1/projects/{id}/pipelines` | Disparar produção após ingest |
