import uuid

import pytest


@pytest.mark.asyncio
async def test_health_ready(client):
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_register_and_login(client):
    uid = uuid.uuid4().hex[:8]
    email = f"user-{uid}@example.com"
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": f"user_{uid}",
            "password": "securepass123",
            "display_name": "Test User",
        },
    )
    assert register.status_code == 200
    assert "access_token" in register.json()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_workspace_rib_and_thread_flow(client, auth_headers):
    workspace = await client.post(
        "/api/v1/workspaces",
        json={"name": "Integration Workspace"},
        headers=auth_headers,
    )
    assert workspace.status_code == 200
    ws_id = workspace.json()["id"]

    ribs = await client.get(f"/api/v1/workspaces/{ws_id}/ribs", headers=auth_headers)
    assert ribs.status_code == 200
    rib_list = ribs.json()
    assert len(rib_list) >= 5
    rib_id = rib_list[0]["id"]

    post = await client.post(
        f"/api/v1/ribs/{rib_id}/posts",
        json={"title": "Hello", "body": "World"},
        headers=auth_headers,
    )
    assert post.status_code == 200
    thread_id = post.json()["id"]

    thread = await client.get(f"/api/v1/threads/{thread_id}", headers=auth_headers)
    assert thread.status_code == 200
    assert thread.json()["post"]["title"] == "Hello"

    comment = await client.post(
        f"/api/v1/threads/{thread_id}/comments",
        json={"body": "First comment"},
        headers=auth_headers,
    )
    assert comment.status_code == 200

    updated = await client.get(f"/api/v1/threads/{thread_id}", headers=auth_headers)
    assert updated.status_code == 200
    assert len(updated.json()["comments"]) == 1


@pytest.mark.asyncio
async def test_list_workspace_agents(client, auth_headers):
    workspace = await client.post(
        "/api/v1/workspaces",
        json={"name": "Agent Workspace"},
        headers=auth_headers,
    )
    ws_id = workspace.json()["id"]

    create = await client.post(
        "/api/v1/agents",
        json={
            "workspace_id": ws_id,
            "display_name": "Test Agent",
            "agent_class": "developer",
        },
        headers=auth_headers,
    )
    assert create.status_code == 200

    listed = await client.get(f"/api/v1/workspaces/{ws_id}/agents", headers=auth_headers)
    assert listed.status_code == 200
    agents = listed.json()
    assert len(agents) == 1
    assert agents[0]["display_name"] == "Test Agent"


@pytest.mark.asyncio
async def test_audit_events(client, auth_headers):
    workspace = await client.post(
        "/api/v1/workspaces",
        json={"name": "Audit Workspace"},
        headers=auth_headers,
    )
    ws_id = workspace.json()["id"]

    audit = await client.get(
        f"/api/v1/audit/events?workspace_id={ws_id}",
        headers=auth_headers,
    )
    assert audit.status_code == 200
    assert len(audit.json()["items"]) >= 1
