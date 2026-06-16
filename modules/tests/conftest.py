import os
import tempfile
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_test_db.name}")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("PROMETHEUS_ENABLED", "false")
os.environ.setdefault("OUTBOX_PUBLISHER_ENABLED", "false")


@pytest.fixture
async def client():
    from apps.api.main import app, lifespan

    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def auth_headers(client):
    uid = uuid.uuid4().hex[:8]
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"user-{uid}@example.com",
            "username": f"user_{uid}",
            "password": "securepass123",
            "display_name": "Integration User",
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
