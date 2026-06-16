from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import Actor, generate_token, require_scopes, resolve_actor
from modules.core.database import get_session
from modules.core.events.service import emit_event, write_audit
from modules.core.models import Agent, TokenRecord

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentCreate(BaseModel):
    workspace_id: uuid.UUID
    display_name: str = Field(min_length=1, max_length=128)
    agent_class: str = Field(default="developer")
    description: str | None = None


class AgentResponse(BaseModel):
    id: str
    workspace_id: str
    display_name: str
    description: str | None
    agent_class: str
    trust_level: str
    is_active: bool
    is_suspended: bool


class TokenCreate(BaseModel):
    scopes: list[str] = Field(default_factory=lambda: ["read:rib", "write:post"])


class TokenResponse(BaseModel):
    token: str
    token_prefix: str
    scopes: list[str]


def _agent_to_response(agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=str(agent.id),
        workspace_id=str(agent.workspace_id),
        display_name=agent.display_name,
        description=agent.description,
        agent_class=agent.agent_class,
        trust_level=agent.trust_level,
        is_active=agent.is_active,
        is_suspended=agent.is_suspended,
    )


@router.post("", response_model=AgentResponse)
async def create_agent(
    body: AgentCreate,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    if actor.type != "human":
        require_scopes(actor, "create:agent")

    agent = Agent(
        workspace_id=body.workspace_id,
        display_name=body.display_name,
        description=body.description,
        agent_class=body.agent_class,
        owner_id=actor.id if actor.type == "human" else None,
    )
    session.add(agent)
    await session.flush()

    await emit_event(
        session,
        event_type="agent.created",
        aggregate_type="agent",
        aggregate_id=agent.id,
        payload={
            "display_name": agent.display_name,
            "agent_class": agent.agent_class,
            "workspace_id": str(agent.workspace_id),
        },
    )
    await write_audit(
        session,
        event_type="agent.created",
        workspace_id=agent.workspace_id,
        actor_id=actor.id,
        actor_type=actor.type,
        resource_type="agent",
        resource_id=agent.id,
        payload={"display_name": agent.display_name},
    )
    await session.commit()
    return _agent_to_response(agent)


@router.post("/{agent_id}/tokens", response_model=TokenResponse)
async def issue_token(
    agent_id: uuid.UUID,
    body: TokenCreate,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent or not agent.is_active or agent.is_suspended:
        raise HTTPException(status_code=404, detail="Agent not found or inactive")

    raw, token_hash, prefix = generate_token()
    record = TokenRecord(
        actor_type="agent",
        actor_id=agent.id,
        workspace_id=agent.workspace_id,
        token_hash=token_hash,
        token_prefix=prefix,
        scopes=body.scopes,
    )
    session.add(record)
    await session.flush()

    await emit_event(
        session,
        event_type="token.issued",
        aggregate_type="token",
        aggregate_id=record.id,
        payload={"agent_id": str(agent.id), "scopes": body.scopes, "prefix": prefix},
    )
    await write_audit(
        session,
        event_type="token.issued",
        workspace_id=agent.workspace_id,
        actor_id=actor.id,
        actor_type=actor.type,
        resource_type="token",
        resource_id=record.id,
        payload={"agent_id": str(agent.id), "prefix": prefix},
    )
    await session.commit()
    return TokenResponse(token=raw, token_prefix=prefix, scopes=body.scopes)


@router.post("/{agent_id}/kill-switch")
async def kill_switch(
    agent_id: uuid.UUID,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_active = False
    agent.is_suspended = True
    now = datetime.now(timezone.utc)
    await session.execute(
        update(TokenRecord)
        .where(TokenRecord.actor_id == agent.id, TokenRecord.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await emit_event(
        session,
        event_type="agent.deactivated",
        aggregate_type="agent",
        aggregate_id=agent.id,
        payload={"reason": "kill_switch"},
    )
    await session.commit()
    return {"status": "deactivated", "agent_id": str(agent.id)}
