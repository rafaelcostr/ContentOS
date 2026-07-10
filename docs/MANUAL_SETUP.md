# Setup manual — ContentOS (pós-automação)

Tudo abaixo exige ação sua. O código já está pronto; estes passos ativam mídia real, publicação e validação em produção.

## 1. API keys de conteúdo (Pexels + Pixabay)

Edite `.env` na raiz do projeto:

```env
PEXELS_API_KEY=sua_chave_aqui
PIXABAY_API_KEY=sua_chave_aqui
CONTENT_SOURCES_ENABLED=pexels,pixabay,local_library,own_library
```

- Pexels: https://www.pexels.com/api/
- Pixabay: https://pixabay.com/api/docs/

Validar (local, fora do container):

```powershell
cd C:\Users\HUNTER\Documents\PROJETOS\ContentOS
python scripts/check_content_sources.py
```

## 2. Reiniciar stack Docker

```powershell
cd C:\Users\HUNTER\Documents\PROJETOS\ContentOS
docker compose -f docker/docker-compose.yml up -d --build agents-worker gateway workflow-engine
```

Confirme que `agents-worker` subiu com as novas env vars.

## 3. E2E factory-full (clipes reais + retention)

```powershell
$env:E2E_WORKFLOW="factory-full"
$env:E2E_TOPIC="GTA 6"
python scripts/e2e_pipeline.py
```

**Sucesso esperado:**

- `real_clip_count > 0` (sem 6 placeholders)
- `retention_passed: true` ou score bem maior que 33
- `quality_passed: true` com loudness ~-16 LUFS
- `thumbnail_qa_passed: true`

Se um step falhar, retry manual:

```powershell
python -c "import httpx; httpx.post('http://localhost:8001/internal/pipelines/<PIPELINE_ID>/retry-step', json={'step':'editor'})"
```

## 4. OAuth das plataformas (dashboard)

1. Abra http://localhost:3000/plugins (ou rota de canais do dashboard)
2. Conecte **TikTok**, **YouTube** e **Instagram** via OAuth
3. Credenciais ficam em `publish_credentials` (Postgres)

## 5. Publicação gradual

| Fase | `PUBLISH_MODE` | O que faz |
|------|----------------|-----------|
| Dev | `dry_run` | Metadados + URLs de preview (padrão) |
| Staging | `prepare_only` | Formata tudo, sem upload |
| Produção | `live` | Upload real + audit em `platform_publications` |

Antes de `live`, confirme:

```env
PUBLISH_REQUIRE_QA=true
QUALITY_REQUIRE_REAL_MEDIA=true
```

TikTok em `live` faz polling pós-upload (`TIKTOK_PUBLISH_POLL_*` no `.env`).

## 6. Kubernetes (se aplicável)

O ConfigMap `k8s/base/configmap.yaml` já inclui `CONTENT_SOURCES_ENABLED=pexels,pixabay,local_library,own_library`. Aplique secrets separados para `PEXELS_API_KEY` e `PIXABAY_API_KEY`.

## 7. Checklist final

- [ ] Pexels e Pixabay respondendo no `check_content_sources.py`
- [ ] Pipeline `factory-full` COMPLETED com clipes reais
- [ ] `platform_publications` com 3 plataformas após publisher
- [ ] OAuth conectado nas 3 redes
- [ ] `prepare_only` testado
- [ ] `live` em canal de teste antes de produção

## Variáveis novas (referência)

| Variável | Default | Uso |
|----------|---------|-----|
| `QUALITY_TARGET_LUFS` | -16 | Alvo de loudness no quality gate |
| `QUALITY_LUFS_TOLERANCE` | 3 | Tolerância ± LUFS |
| `TIKTOK_PUBLISH_POLL_INTERVAL_SEC` | 3 | Intervalo de polling TikTok |
| `TIKTOK_PUBLISH_POLL_TIMEOUT_SEC` | 120 | Timeout de polling TikTok |
