from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import Actor, generate_token, resolve_actor
from modules.core.database import get_session
from modules.core.events.service import emit_event, write_audit
from modules.core.models import Agent, Rib, TokenRecord

router = APIRouter(prefix="/provisioning", tags=["provisioning"])

MAX_AGENTS_PER_INSTALL = 20


class AgentSpec(BaseModel):
    display_name: str
    agent_class: str = "developer"
    role_name: str = "developer-agent"
    rib_slugs: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=lambda: ["read:rib", "write:post"])


class ValidateRequest(BaseModel):
    workspace_id: uuid.UUID
    agents: list[AgentSpec]


class InstallationRequest(BaseModel):
    workspace_id: uuid.UUID
    agents: list[AgentSpec]


class InstallationResponse(BaseModel):
    id: str
    status: str
    steps: list[dict]
    result: dict | None = None


POLICY_PACKS = {
    "open_lab": {"max_agents": 50, "allowed_scopes": ["read:rib", "write:post", "moderate:thread"]},
    "private_team": {"max_agents": 20, "allowed_scopes": ["read:rib", "write:post", "moderate:thread", "create:agent"]},
    "enterprise": {"max_agents": 100, "allowed_scopes": ["read:rib", "write:post", "moderate:thread", "create:agent", "issue:token", "manage:policy"]},
}


@router.post("/validate")
async def validate_provisioning(
    body: ValidateRequest,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    errors: list[str] = []
    if len(body.agents) > MAX_AGENTS_PER_INSTALL:
        errors.append(f"Maximum {MAX_AGENTS_PER_INSTALL} agents per installation")
    if len(body.agents) == 0:
        errors.append("At least one agent required")

    existing_count = (
        await session.execute(
            select(func.count()).select_from(Agent).where(Agent.workspace_id == body.workspace_id)
        )
    ).scalar_one()
    if existing_count + len(body.agents) > 50:
        errors.append("Workspace agent limit exceeded")

    rib_slugs = {spec.rib_slug for spec in body.agents for rib_slug in spec.rib_slugs}
    if rib_slugs:
        ribs = (
            await session.execute(
                select(Rib.slug).where(Rib.workspace_id == body.workspace_id, Rib.slug.in_(rib_slugs))
            )
        ).scalars().all()
        missing = rib_slugs - set(ribs)
        if missing:
            errors.append(f"Unknown rib slugs: {', '.join(sorted(missing))}")

    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/installations", response_model=InstallationResponse)
async def create_installation(
    body: InstallationRequest,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    validation = await validate_provisioning(
        ValidateRequest(workspace_id=body.workspace_id, agents=body.agents),
        actor,
        session,
    )
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={"errors": validation["errors"]})

    installation_id = uuid.uuid4()
    steps = [{"name": "validate", "status": "completed"}]
    created_agents: list[dict] = []
    credentials: list[dict] = []

    for spec in body.agents:
        agent = Agent(
            workspace_id=body.workspace_id,
            display_name=spec.display_name,
            agent_class=spec.agent_class,
            owner_id=actor.id if actor.type == "human" else None,
        )
        session.add(agent)
        await session.flush()
        created_agents.append({"id": str(agent.id), "display_name": agent.display_name})

        raw, token_hash, prefix = generate_token()
        record = TokenRecord(
            actor_type="agent",
            actor_id=agent.id,
            workspace_id=body.workspace_id,
            token_hash=token_hash,
            token_prefix=prefix,
            scopes=spec.scopes,
        )
        session.add(record)
        credentials.append(
            {
                "agent_id": str(agent.id),
                "display_name": agent.display_name,
                "token": raw,
                "token_prefix": prefix,
                "scopes": spec.scopes,
            }
        )
        await emit_event(
            session,
            event_type="agent.created",
            aggregate_type="agent",
            aggregate_id=agent.id,
            payload={"display_name": agent.display_name, "provisioning": True},
        )

    steps.append({"name": "create_agents", "status": "completed", "detail": {"count": len(created_agents)}})
    steps.append({"name": "issue_tokens", "status": "completed"})

    await write_audit(
        session,
        event_type="provisioning.completed",
        workspace_id=body.workspace_id,
        actor_id=actor.id,
        actor_type=actor.type,
        payload={"installation_id": str(installation_id), "agent_count": len(created_agents)},
    )
    await session.commit()

    return InstallationResponse(
        id=str(installation_id),
        status="completed",
        steps=steps,
        result={"agents": created_agents, "credentials": credentials},
    )
