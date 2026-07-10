"""E2E Growth API smoke test — Fase 18.

Prerequisites:
  docker compose -f docker/docker-compose.yml up -d
  python scripts/wait_for_services.py

Usage:
  python scripts/e2e_growth.py
  $env:GATEWAY_URL = "http://localhost:8000"
  $env:E2E_PROJECT_ID = "<uuid>"
"""

from __future__ import annotations

import os
import sys

import httpx

GATEWAY = os.getenv("GATEWAY_URL", "http://localhost:8000").rstrip("/")
PROJECT_ID = os.getenv("E2E_PROJECT_ID", "").strip()
TIMEOUT = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=30.0)


def _auth_headers(client: httpx.Client) -> dict[str, str]:
    email = os.getenv("E2E_EMAIL", "admin@contentos.local")
    password = os.getenv("E2E_PASSWORD", "admin123")
    resp = client.post(f"{GATEWAY}/api/v1/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed: {resp.status_code} {resp.text}")
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    print(f"Growth E2E smoke → {GATEWAY}")
    with httpx.Client(timeout=TIMEOUT) as client:
        headers = _auth_headers(client)

        health = client.get(f"{GATEWAY}/api/v1/growth/health", headers=headers)
        print(f"GET /growth/health → {health.status_code}")
        if health.status_code != 200:
            print(health.text)
            return 1
        print(f"  status: {health.json().get('status')}")

        projects = client.get(f"{GATEWAY}/api/v1/projects", headers=headers)
        if projects.status_code != 200:
            print(f"Projects failed: {projects.status_code}")
            return 1
        project_id = PROJECT_ID
        if not project_id:
            rows = projects.json()
            if not rows:
                print("No projects — create one first")
                return 1
            project_id = rows[0]["id"]
        print(f"  project_id: {project_id}")

        for path in (
            f"/api/v1/growth/report?project_id={project_id}",
            f"/api/v1/growth/channels?project_id={project_id}",
            f"/api/v1/growth/calendar?project_id={project_id}",
            f"/api/v1/growth/recommendations?project_id={project_id}",
            f"/api/v1/growth/oauth-audit?project_id={project_id}",
            f"/api/v1/growth/history?project_id={project_id}",
            f"/api/v1/growth/performance?project_id={project_id}",
        ):
            resp = client.get(f"{GATEWAY}{path}", headers=headers)
            print(f"GET {path.split('?')[0]} → {resp.status_code}")
            if resp.status_code >= 400:
                print(resp.text[:300])
                return 1

    print("Growth E2E smoke OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
