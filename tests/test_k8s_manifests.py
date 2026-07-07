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
    assert "agents-worker-v5-quality-scaler" in out
    assert "contentos.retention" in out
    assert "contentos.media_analyze" in out


def test_kustomize_keda_overlay_general_multi_trigger():
    out = _kustomize_build(K8S / "overlays" / "autoscaling-keda")
    assert out.count("listName: contentos.publisher") >= 1
    assert "listName: contentos.analytics" in out
    assert "listName: contentos.learning" in out


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
    v5_pools = (K8S / "base" / "agents-worker-pools-v5.yaml").read_text(encoding="utf-8")
    assert "contentos.research" in pools
    assert "contentos.editor" in pools
    assert "contentos.publisher" in pools
    assert "contentos.retention" in v5_pools
    assert "contentos.media_analyze" in v5_pools
    assert "contentos.quality" in v5_pools
    assert "contentos.learning" in pools
    assert "contentos.multi_content" in pools
    # V5 queues must not remain on general pool
    assert "contentos.retention" not in pools
    assert "contentos.media_analyze" not in pools


def test_v5_queues_mapped_once():
    """Each V5 queue appears in exactly one worker pool manifest."""
    general = (K8S / "base" / "agents-worker-pools.yaml").read_text(encoding="utf-8")
    v5 = (K8S / "base" / "agents-worker-pools-v5.yaml").read_text(encoding="utf-8")
    v5_queues = [
        "contentos.retention",
        "contentos.seo",
        "contentos.ai_director",
        "contentos.creative_memory",
        "contentos.media_analyze",
        "contentos.asset_collector",
        "contentos.clip_research",
    ]
    for q in v5_queues:
        assert q in v5, q
        assert q not in general, q


def test_kustomize_production_overlay():
    out = _kustomize_build(K8S / "overlays" / "production")
    assert "kind: Ingress" in out
    assert "APP_ENV: production" in out
    assert "kind: ExternalSecret" in out
    assert "agents-worker-v5-quality" in out
    assert "agents-worker-v5-media" in out
    assert "maxReplicaCount: 12" in out
    assert "/health/ready" in out
    assert "GATEWAY_RATE_LIMIT_ENABLED" in out

