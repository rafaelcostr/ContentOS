"""Seed — register user, create project, upload placeholder, start pipeline."""

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path

import httpx

GATEWAY = os.getenv("GATEWAY_URL", "http://localhost:8000")


async def main() -> None:
    async with httpx.AsyncClient(timeout=120.0) as client:
        email, password = "admin@contentos.dev", "admin123"

        reg = await client.post(
            f"{GATEWAY}/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Admin",
            },
        )
        if reg.status_code not in (201, 400):
            reg.raise_for_status()

        login = await client.post(f"{GATEWAY}/api/v1/auth/login", json={"email": email, "password": password})
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        project = await client.post(
            f"{GATEWAY}/api/v1/projects",
            json={
                "name": "Demo Content",
                "description": "Projeto de demonstração",
            },
            headers=headers,
        )
        project.raise_for_status()
        project_id = project.json()["id"]
        print(f"Project: {project_id}")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=0x1e1b4b:s=1080x1920:d=5",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(tmp_path),
                ],
                check=True,
                capture_output=True,
            )
            with open(tmp_path, "rb") as f:
                upload = await client.post(
                    f"{GATEWAY}/api/v1/assets/takes/upload",
                    headers=headers,
                    data={"theme": "GTA 6", "label": "intro", "project_id": project_id},
                    files={"file": ("intro.mp4", f, "video/mp4")},
                )
            upload.raise_for_status()
            print(f"Take uploaded: {upload.json()['id']}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("FFmpeg not available — skip take upload")
        finally:
            tmp_path.unlink(missing_ok=True)

        pipeline = await client.post(
            f"{GATEWAY}/api/v1/projects/{project_id}/pipelines",
            json={"topic": "GTA 6"},
            headers=headers,
        )
        pipeline.raise_for_status()
        data = pipeline.json()
        print(f"Pipeline: {data['id']} — {data['status']}")
        print("Dashboard: http://localhost:3000/projects")


if __name__ == "__main__":
    asyncio.run(main())
