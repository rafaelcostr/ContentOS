# ContentOS — CI/CD

## Pipeline GitHub Actions

| Job | Descrição |
|-----|-----------|
| `lint-python` | Ruff check + format |
| `test-unit` | pytest unitário (sem Postgres) |
| `test-v2` | pytest pacotes V2 (workflow, event bus, plugins, etc.) |
| `test-integration` | API integration com Postgres |
| `lint-dashboard` | next lint |
| `build-dashboard` | next build |
| `e2e-playwright` | Playwright smoke tests |
| `docker-build` | Build imagens Docker |
| `k8s-validate` | kubectl kustomize (base + overlays) |
| `deploy-staging` | Push `develop` → GHCR + optional kubectl apply |

Trigger: push/PR em `main`, `master`, `develop`. Deploy staging: push em `develop` ou manual.

---

## Local — testes

```powershell
# Unitários (sem Postgres)
pip install -r requirements-dev.txt
pytest tests/ -v -m "not integration" --ignore=tests/test_api_integration.py

# Integração (requer Postgres)
$env:DATABASE_URL = "postgresql+asyncpg://contentos:contentos_secret@localhost:5432/contentos"
pytest tests/test_api_integration.py -v

# Lint Python
ruff check packages apps/backend/src services tests
ruff format --check packages apps/backend/src services tests

# Playwright E2E
cd apps/dashboard
npm install
npx playwright install chromium
npm run test:e2e
```

---

## Local — pipeline E2E completo

```powershell
docker compose -f docker/docker-compose.yml up -d --build
python scripts/wait_for_services.py
python scripts/e2e_pipeline.py
```

---

## Docker build manual

```powershell
docker build -f docker/Dockerfile.gateway -t contentos/gateway .
docker build -f docker/Dockerfile.agent -t contentos/agents-worker .
docker build -f docker/Dockerfile.workflow -t contentos/workflow-engine .
```

---

## Scale workers (Docker Compose)

```powershell
docker compose -f docker/docker-compose.yml -f docker/docker-compose.scale.yml up -d
```

---

## Kubernetes

Ver [K8S.md](./K8S.md).

```powershell
kubectl apply -k k8s/base/
```

---

## Staging deploy (Tier E5)

Ver [DEPLOY_STAGING.md](./DEPLOY_STAGING.md).

```powershell
# Automático no push para develop (GitHub Actions)
# Secret necessário para apply: STAGING_KUBECONFIG (base64)
```

---

## Variáveis CI

| Variável | Job |
|----------|-----|
| `DATABASE_URL` | test-integration |
| `JWT_SECRET` | test-integration |
| `PLAYWRIGHT_API_URL` | e2e full stack (opcional) |
