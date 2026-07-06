"""Tier E3 — Grafana dashboard provisioning."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAFANA = ROOT / "docker" / "grafana" / "provisioning"


def test_datasource_provisioning_exists():
    assert (GRAFANA / "datasources" / "datasources.yml").is_file()


def test_dashboard_provider_exists():
    assert (GRAFANA / "dashboards" / "dashboards.yml").is_file()


def test_dashboard_json_files_valid():
    json_dir = GRAFANA / "dashboards" / "json"
    files = list(json_dir.glob("*.json"))
    assert len(files) >= 2
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "title" in data
        assert "uid" in data
        assert "panels" in data
        assert len(data["panels"]) >= 1


def test_overview_dashboard_queries():
    data = json.loads((GRAFANA / "dashboards" / "json" / "contentos-overview.json").read_text(encoding="utf-8"))
    exprs = []
    for panel in data["panels"]:
        for target in panel.get("targets", []):
            if "expr" in target:
                exprs.append(target["expr"])
    assert "contentos_cpu_percent" in exprs
    assert "contentos_postgres_up" in exprs


def test_production_dashboard_queries():
    data = json.loads((GRAFANA / "dashboards" / "json" / "contentos-production.json").read_text(encoding="utf-8"))
    exprs = []
    for panel in data["panels"]:
        for target in panel.get("targets", []):
            if "expr" in target:
                exprs.append(target["expr"])
    assert "contentos_celery_queue_depth" in exprs
    assert "contentos_pipelines_total" in exprs
