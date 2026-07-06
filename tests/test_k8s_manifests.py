"""Tier E4/E5 — Kubernetes manifests and staging overlay."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
K8S = ROOT / "k8s"


def _kustomize_build(path: Path) -> str:
    result = subprocess.run(
        ["kubectl", "kustomize", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_kustomize_base_builds():
    out = _kustomize_build(K8S / "base")
    assert "agents-worker-research" in out
    assert "agents-worker-editor" in out


def test_kustomize_keda_overlay():
    out = _kustomize_build(K8S / "overlays" / "autoscaling-keda")
    assert "kind: ScaledObject" in out
    assert "contentos.research" in out


def test_kustomize_cpu_overlay():
    out = _kustomize_build(K8S / "overlays" / "autoscaling-cpu")
    assert "kind: HorizontalPodAutoscaler" in out
    assert "agents-worker-research-hpa" in out


def test_kustomize_staging_overlay():
    out = _kustomize_build(K8S / "overlays" / "staging")
    assert "namespace: contentos-staging" in out
    assert "APP_ENV: staging" in out


def test_worker_pools_cover_queues():
    pools = (K8S / "base" / "agents-worker-pools.yaml").read_text(encoding="utf-8")
    assert "contentos.research" in pools
    assert "contentos.editor" in pools
    assert "contentos.publisher" in pools


def test_kustomize_production_overlay():
    out = _kustomize_build(K8S / "overlays" / "production")
    assert "kind: Ingress" in out
    assert "APP_ENV: production" in out
    assert "kind: ExternalSecret" in out
