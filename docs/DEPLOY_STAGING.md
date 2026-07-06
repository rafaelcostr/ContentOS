# Deploy Staging (Tier E5)

Continuous deployment to a **staging** Kubernetes namespace on push to `develop`.

## Pipeline

Workflow: `.github/workflows/deploy-staging.yml`

| Job | Description |
|-----|-------------|
| `test` | Unit tests + `kubectl kustomize` validation |
| `build-push` | Build & push 5 images to GHCR (`:staging`, `:staging-<sha>`) |
| `deploy` | `kubectl apply -k k8s/overlays/staging` (when cluster secret is set) |

Trigger: push to `develop` or manual `workflow_dispatch`.

## One-time setup

### 1. GitHub secrets

| Secret | Description |
|--------|-------------|
| `STAGING_KUBECONFIG` | Base64-encoded kubeconfig for staging cluster |

```bash
cat ~/.kube/config-staging | base64 -w0
```

If unset, CI still builds and pushes images; deploy step is skipped.

### 2. GitHub environment

Create environment **staging** in repo settings (optional protection rules / reviewers).

### 3. KEDA on cluster (queue autoscaling)

```bash
kubectl apply -f https://github.com/kedacore/keda/releases/download/v2.16.0/keda-2.16.0.yaml
```

### 4. Infrastructure

Staging expects PostgreSQL, Redis, MinIO, Ollama, Piper, Whisper — same as production (managed or in-cluster). Update `k8s/base/secret.yaml` values via sealed-secrets or external secret operator before first deploy.

## Image registry

Images are published to:

```
ghcr.io/<owner>/<repo>/gateway:staging-<sha>
ghcr.io/<owner>/<repo>/workflow-engine:staging-<sha>
ghcr.io/<owner>/<repo>/agents-worker:staging-<sha>
ghcr.io/<owner>/<repo>/ai-gateway:staging-<sha>
ghcr.io/<owner>/<repo>/dashboard:staging-<sha>
```

Enable **Packages** write permission for `GITHUB_TOKEN` (default in workflow).

## Manual deploy

```powershell
# Build & tag locally
$env:IMAGE_ROOT = "ghcr.io/your-org/your-repo"
$env:TAG = "staging-manual"

cd k8s/overlays/staging
kustomize edit set image contentos/gateway=${IMAGE_ROOT}/gateway:${TAG} ...
kubectl apply -k .
```

Or use the helper script:

```powershell
./scripts/deploy_staging.ps1 -ImageRoot ghcr.io/org/repo -Tag staging-abc123
```

## Staging overlay

- Namespace: `contentos-staging`
- `APP_ENV=staging`, `DEBUG=true`
- Reduced replicas (gateway/dashboard/general pool)
- KEDA queue autoscaling (via `autoscaling-keda` overlay)

## Related

- [K8S.md](./K8S.md) — worker pools & HPA/KEDA
- [CI_CD.md](./CI_CD.md) — full CI pipeline
