from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import Actor, resolve_actor
from modules.core.database import get_session
from modules.core.events.service import emit_event, write_audit
from modules.core.models import Agent, Rib, Workspace

router = APIRouter(tags=["workspace"])

DEFAULT_RIBS = [
    ("Management", "management", "Planning and coordination"),
    ("Development", "dev", "Implementation updates"),
    ("QA", "qa", "Testing and quality"),
    ("Issues", "issues", "Bugs and defects"),
    ("Requests", "requests", "Incoming work requests"),
]


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str


class RibResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    slug: str
    description: str | None
    visibility: str
    is_archived: bool
    is_locked: bool


class AgentResponse(BaseModel):
    id: str
    workspace_id: str
    display_name: str
    description: str | None
    agent_class: str
    trust_level: str
    is_active: bool
    is_suspended: bool


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:64] or "workspace"


def _rib_to_response(rib: Rib) -> RibResponse:
    return RibResponse(
        id=str(rib.id),
        workspace_id=str(rib.workspace_id),
        name=rib.name,
        slug=rib.slug,
        description=rib.description,
        visibility=rib.visibility,
        is_archived=rib.is_archived,
        is_locked=rib.is_locked,
    )


@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(
    body: WorkspaceCreate,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    if actor.type != "human":
        raise HTTPException(status_code=403, detail="Only humans can create workspaces")

    base_slug = _slugify(body.name)
    slug = base_slug
    suffix = 1
    while (await session.execute(select(Workspace).where(Workspace.slug == slug))).scalar_one_or_none():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    workspace = Workspace(name=body.name, slug=slug, owner_id=actor.id)
    session.add(workspace)
    await session.flush()

    for name, rib_slug, description in DEFAULT_RIBS:
        session.add(
            Rib(
                workspace_id=workspace.id,
                name=name,
                slug=rib_slug,
                description=description,
            )
        )

    await emit_event(
        session,
        event_type="workspace.created",
        aggregate_type="workspace",
        aggregate_id=workspace.id,
        payload={"name": workspace.name, "slug": workspace.slug},
    )
    await write_audit(
        session,
        event_type="workspace.created",
        workspace_id=workspace.id,
        actor_id=actor.id,
        actor_type="human",
        resource_type="workspace",
        resource_id=workspace.id,
        payload={"name": workspace.name},
    )
    await session.commit()
    return WorkspaceResponse(id=str(workspace.id), name=workspace.name, slug=workspace.slug)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    workspace = (
        await session.execute(select(Workspace).where(Workspace.id == workspace_id))
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse(id=str(workspace.id), name=workspace.name, slug=workspace.slug)


@router.get("/workspaces/{workspace_id}/ribs", response_model=list[RibResponse])
async def list_ribs(
    workspace_id: uuid.UUID,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    ribs = (
        await session.execute(
            select(Rib).where(Rib.workspace_id == workspace_id, Rib.is_archived.is_(False)).order_by(Rib.name)
        )
    ).scalars().all()
    return [_rib_to_response(rib) for rib in ribs]


@router.get("/workspaces/{workspace_id}/agents", response_model=list[AgentResponse])
async def list_workspace_agents(
    workspace_id: uuid.UUID,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    agents = (
        await session.execute(
            select(Agent).where(Agent.workspace_id == workspace_id).order_by(Agent.display_name)
        )
    ).scalars().all()
    return [
        AgentResponse(
            id=str(agent.id),
            workspace_id=str(agent.workspace_id),
            display_name=agent.display_name,
            description=agent.description,
            agent_class=agent.agent_class,
            trust_level=agent.trust_level,
            is_active=agent.is_active,
            is_suspended=agent.is_suspended,
        )
        for agent in agents
    ]


@router.get("/ribs/{rib_id}", response_model=RibResponse)
async def get_rib(
    rib_id: uuid.UUID,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    rib = (await session.execute(select(Rib).where(Rib.id == rib_id))).scalar_one_or_none()
    if not rib:
        raise HTTPException(status_code=404, detail="Rib not found")
    return _rib_to_response(rib)
