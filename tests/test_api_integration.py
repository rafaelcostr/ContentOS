"""API integration tests — FastAPI gateway with PostgreSQL."""

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.integration

# Ensure test env before app import
os.environ.setdefault("JWT_SECRET", "test-secret-ci")
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://contentos:contentos_secret@localhost:5432/contentos",
    ),
)

from contentos_database.session import create_tables, init_db  # noqa: E402
from contentos_gateway.main import app  # noqa: E402


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    init_db(os.environ["DATABASE_URL"], echo=False)
    await create_tables()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"test-{uuid.uuid4().hex[:8]}@contentos.dev"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Test"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_auth_register_login(client: AsyncClient):
    email = f"user-{uuid.uuid4().hex[:8]}@contentos.dev"
    reg = await client.post("/api/v1/auth/register", json={"email": email, "password": "secret123", "full_name": "U"})
    assert reg.status_code in (201, 400)
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "secret123"})
    assert login.status_code == 200
    assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_projects_crud(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "CI Project", "description": "Integration test"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    project = create.json()
    assert project["name"] == "CI Project"

    listing = await client.get("/api/v1/projects", headers=auth_headers)
    assert listing.status_code == 200
    assert any(p["id"] == project["id"] for p in listing.json())


@pytest.mark.asyncio
async def test_plugins_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/plugins", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "plugins" in data
    names = {p["name"] for p in data["plugins"]}
    assert "tiktok" in names
    assert "youtube" in names
    assert "instagram" in names


@pytest.mark.asyncio
async def test_providers_status(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/providers/status", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["text"] in ("ollama", "openai")


@pytest.mark.asyncio
async def test_agents_list(client: AsyncClient):
    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) == 9
    assert agents[0]["provider"] is not None


@pytest.mark.asyncio
async def test_metrics_system_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/metrics/system")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_metrics_system(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/metrics/system", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "cpu" in data
    assert "memory" in data
