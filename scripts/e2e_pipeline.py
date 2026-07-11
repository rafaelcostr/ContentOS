"""E2E pipeline test — full local stack without paid APIs.

Prerequisites:
  docker compose -f docker/docker-compose.yml up -d --build
  python scripts/wait_for_services.py

Usage:
  python scripts/e2e_pipeline.py

  # V2 dynamic (16 steps)
  $env:E2E_WORKFLOW = "v2-dynamic"
  python scripts/e2e_pipeline.py

  # V5 media autopilot (14 steps, GTA 6 default topic)
  $env:E2E_WORKFLOW = "v5-media-autopilot"
  $env:E2E_TOPIC = "GTA 6"
  python scripts/e2e_pipeline.py

  # Factory full (31 steps — long run, ~30–90 min local)
  $env:E2E_WORKFLOW = "factory-full"
  $env:E2E_TOPIC = "GTA 6"
  python scripts/e2e_pipeline.py

  # Resume polling an existing pipeline (after script crash)
  $env:E2E_PIPELINE_ID = "3da79fa9-0a86-4038-8512-ab83a051116f"
  python scripts/e2e_pipeline.py
"""

import asyncio
import os
import sys
import time
from collections.abc import Awaitable, Callable

# Line-buffer stdout so background E2E runs show progress immediately on Windows.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

import httpx

GATEWAY = os.getenv("GATEWAY_URL", "http://localhost:8000")
TOPIC = os.getenv("E2E_TOPIC", "GTA 6")
WORKFLOW_TEMPLATE = os.getenv("E2E_WORKFLOW", "v1-default")
RESUME_PIPELINE_ID = os.getenv("E2E_PIPELINE_ID", "").strip()
POLL_INTERVAL = int(os.getenv("E2E_POLL_SECONDS", "15"))
PIPELINE_TIMEOUT = int(os.getenv("E2E_TIMEOUT_SECONDS", "3600"))
HTTP_RETRIES = int(os.getenv("E2E_HTTP_RETRIES", "8"))

RETRYABLE = (
    httpx.ReadError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
    httpx.WriteError,
)

HTTP_TIMEOUT = httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0)


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(HTTP_RETRIES):
        try:
            response = await client.request(method, url, **kwargs)
            return response
        except RETRYABLE as exc:
            last_exc = exc
            if attempt >= HTTP_RETRIES - 1:
                break
            wait = min(2**attempt, 30)
            print(
                f"  [retry {attempt + 1}/{HTTP_RETRIES}] {exc.__class__.__name__} — aguardando {wait}s...",
                file=sys.stderr,
            )
            await asyncio.sleep(wait)
    assert last_exc is not None
    raise last_exc


async def login_headers(
    client: httpx.AsyncClient,
    email: str,
    password: str,
) -> dict[str, str]:
    login = await request_with_retry(
        client,
        "POST",
        f"{GATEWAY}/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    login.raise_for_status()
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def wait_for_pipeline(
    client: httpx.AsyncClient,
    pipeline_id: str,
    headers: dict[str, str],
    *,
    reauth: Callable[[], Awaitable[dict[str, str]]] | None = None,
) -> dict:
    """Poll pipeline status via Gateway API (stable; survives workflow-engine restarts)."""
    deadline = time.monotonic() + PIPELINE_TIMEOUT
    last_status = ""

    while time.monotonic() < deadline:
        resp = await request_with_retry(
            client,
            "GET",
            f"{GATEWAY}/api/v1/pipelines/{pipeline_id}",
            headers=headers,
        )
        if resp.status_code == 401 and reauth:
            headers.update(await reauth())
            print("  [auth] Token refreshed — resuming poll", file=sys.stderr)
            resp = await request_with_retry(
                client,
                "GET",
                f"{GATEWAY}/api/v1/pipelines/{pipeline_id}",
                headers=headers,
            )
        resp.raise_for_status()
        pdata = resp.json()
        status = pdata["status"]
        step = pdata.get("current_step") or "—"
        job_list = pdata.get("jobs", [])

        summary = " | ".join(f"{j['step']}:{j['status']}" for j in job_list)
        line = f"Pipeline {status} @ {step} — [{summary}]"
        if line != last_status:
            print(line)
            last_status = line

        if status == "completed":
            return {"status": "completed", "jobs": job_list}
        if status == "failed":
            failed = [j for j in job_list if j["status"] == "failed"]
            return {
                "status": "failed",
                "jobs": job_list,
                "failed": failed,
                "error": pdata.get("error_message"),
            }

        await asyncio.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Pipeline did not finish within {PIPELINE_TIMEOUT}s")


async def cancel_stale_pipelines(
    client: httpx.AsyncClient,
    headers: dict[str, str],
) -> int:
    """Cancel running/pending pipelines for the current org (frees concurrent quota)."""
    resp = await request_with_retry(
        client,
        "GET",
        f"{GATEWAY}/api/v1/pipelines?limit=50",
        headers=headers,
    )
    resp.raise_for_status()
    cancelled = 0
    for pipe in resp.json():
        if pipe.get("status") not in ("running", "pending"):
            continue
        pid = pipe["id"]
        cancel = await request_with_retry(
            client,
            "POST",
            f"{GATEWAY}/api/v1/pipelines/{pid}/cancel",
            headers=headers,
        )
        if cancel.status_code in (200, 400):
            cancelled += 1
            print(f"  Cancelled stale pipeline: {pid} ({pipe.get('topic')})")
    return cancelled


async def main() -> int:
    email = os.getenv("E2E_EMAIL", "e2e@contentos.dev")
    password = os.getenv("E2E_PASSWORD", "e2e123456")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        print("=== ContentOS E2E Pipeline (local AI stack) ===\n")

        # 1. Auth
        reg = await request_with_retry(
            client,
            "POST",
            f"{GATEWAY}/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "E2E Test"},
        )
        if reg.status_code not in (201, 400):
            reg.raise_for_status()

        login = await request_with_retry(
            client,
            "POST",
            f"{GATEWAY}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        login.raise_for_status()
        headers = await login_headers(client, email, password)
        print(f"Authenticated: {email}")

        async def reauth() -> dict[str, str]:
            return await login_headers(client, email, password)

        if RESUME_PIPELINE_ID:
            pipeline_id = RESUME_PIPELINE_ID
            detail = await request_with_retry(
                client,
                "GET",
                f"{GATEWAY}/api/v1/pipelines/{pipeline_id}",
                headers=headers,
            )
            detail.raise_for_status()
            pdata = detail.json()
            print(f"Resuming pipeline: {pipeline_id}")
            print(f"  topic: {pdata.get('topic')} — workflow: {pdata.get('workflow_name')}")
            print(f"  status: {pdata.get('status')} @ {pdata.get('current_step') or '—'}\n")
        else:
            # 2. Provider health
            health = await request_with_retry(
                client,
                "GET",
                f"{GATEWAY}/api/v1/providers/health",
                headers=headers,
            )
            health.raise_for_status()
            hdata = health.json()
            print(f"Providers healthy: {hdata['all_healthy']}")
            for p in hdata["providers"]:
                icon = "OK" if p["healthy"] else "FAIL"
                print(f"  {icon} {p['name']}: {p['detail']}")
            if not hdata["all_healthy"]:
                print("\nProviders not ready — run: python scripts/wait_for_services.py", file=sys.stderr)
                return 1

            if WORKFLOW_TEMPLATE in ("factory-full", "v5-media-autopilot", "v2-dynamic"):
                cs = await request_with_retry(
                    client,
                    "GET",
                    f"{GATEWAY}/api/v1/content-sources/health",
                    headers=headers,
                )
                if cs.status_code == 200:
                    for src in cs.json().get("sources", []):
                        icon = "OK" if src.get("healthy") else "FAIL"
                        print(f"  {icon} content-source/{src.get('source_id')}: {src.get('message', '')}")
                    if not any(
                        s.get("source_id") in ("local_library", "own_library") and s.get("healthy")
                        for s in cs.json().get("sources", [])
                    ):
                        print(
                            "\nWARN: No healthy local library — Media Collector should upload takes "
                            "via POST /api/v1/assets/takes/upload before production pipelines.",
                            file=sys.stderr,
                        )

            # 3. Project
            project = await request_with_retry(
                client,
                "POST",
                f"{GATEWAY}/api/v1/projects",
                json={"name": "E2E Local Stack", "description": "Pipeline test without paid APIs"},
                headers=headers,
            )
            project.raise_for_status()
            project_id = project.json()["id"]
            print(f"Project: {project_id}")

            # 4. Start pipeline
            body: dict = {"topic": TOPIC}
            if WORKFLOW_TEMPLATE and WORKFLOW_TEMPLATE != "v1-default":
                body["workflow_name"] = WORKFLOW_TEMPLATE
            pipeline = await request_with_retry(
                client,
                "POST",
                f"{GATEWAY}/api/v1/projects/{project_id}/pipelines",
                json=body,
                headers=headers,
            )
            if pipeline.status_code == 429:
                detail = pipeline.json().get("detail", {})
                if detail.get("kind") == "concurrent_pipelines":
                    print("Concurrent quota full — cancelling stale pipelines...")
                    n = await cancel_stale_pipelines(client, headers)
                    if n:
                        pipeline = await request_with_retry(
                            client,
                            "POST",
                            f"{GATEWAY}/api/v1/projects/{project_id}/pipelines",
                            json=body,
                            headers=headers,
                        )
            if pipeline.status_code >= 400:
                print(f"Pipeline create failed ({pipeline.status_code}): {pipeline.text}", file=sys.stderr)
            pipeline.raise_for_status()
            pipeline_id = pipeline.json()["id"]
            wf_label = pipeline.json().get("workflow_name") or WORKFLOW_TEMPLATE
            print(f"Pipeline started: {pipeline_id} — topic: {TOPIC} — workflow: {wf_label}\n")

        # 5. Poll until done
        result = await wait_for_pipeline(client, pipeline_id, headers, reauth=reauth)

        print(f"\n=== Result: {result['status'].upper()} ===")
        for j in result["jobs"]:
            mark = "OK" if j["status"] == "completed" else "FAIL"
            print(f"  {mark} {j['step']}: {j['status']}")

        if result["status"] != "completed":
            if result.get("error"):
                print(f"Error: {result['error']}", file=sys.stderr)
            return 1

        # 6. Optional: publish audit log (factory-full / publisher step)
        if WORKFLOW_TEMPLATE in ("factory-full", "v5-media-autopilot", "v1-default"):
            detail = await request_with_retry(
                client,
                "GET",
                f"{GATEWAY}/api/v1/pipelines/{pipeline_id}",
                headers=headers,
            )
            detail.raise_for_status()
            project_id = detail.json().get("project_id")
            if project_id:
                attempts = await request_with_retry(
                    client,
                    "GET",
                    f"{GATEWAY}/api/v1/publish/attempts?project_id={project_id}",
                    headers=headers,
                )
                if attempts.status_code == 200:
                    rows = attempts.json()
                    print(f"\nPublish attempts logged: {len(rows)}")
                    for row in rows[:5]:
                        print(
                            f"  - {row.get('platform')}: {row.get('status')} "
                            f"({row.get('publish_mode')})"
                        )

        print("\nE2E pipeline completed successfully.")
        print("Dashboard: http://localhost:3000/jobs")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except TimeoutError as exc:
        print(f"\n{exc}", file=sys.stderr)
        raise SystemExit(1)
    except httpx.HTTPStatusError as exc:
        print(f"\nHTTP {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
        raise SystemExit(1)
    except RETRYABLE as exc:
        print(
            f"\nConexão perdida com o Gateway ({GATEWAY}): {exc}",
            file=sys.stderr,
        )
        print("Verifique: docker compose ps && curl http://localhost:8000/health", file=sys.stderr)
        raise SystemExit(1)
