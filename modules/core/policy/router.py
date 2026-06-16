from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import Actor, resolve_actor
from modules.core.database import get_session
from modules.core.models import Policy
from modules.core.provisioning.router import POLICY_PACKS

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicyCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str = Field(min_length=1, max_length=128)
    policy_pack: str = "private_team"


class PolicyResponse(BaseModel):
    id: str
    name: str
    policy_pack: str
    rules: dict


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    workspace_id: uuid.UUID,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    policies = (
        await session.execute(select(Policy).where(Policy.workspace_id == workspace_id).order_by(Policy.name))
    ).scalars().all()
    return [
        PolicyResponse(id=str(p.id), name=p.name, policy_pack=p.policy_pack, rules=dict(p.rules or {}))
        for p in policies
    ]


@router.post("", response_model=PolicyResponse)
async def create_policy(
    body: PolicyCreate,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    rules = POLICY_PACKS.get(body.policy_pack, POLICY_PACKS["private_team"])
    policy = Policy(
        workspace_id=body.workspace_id,
        name=body.name,
        policy_pack=body.policy_pack,
        rules=rules,
    )
    session.add(policy)
    await session.commit()
    return PolicyResponse(
        id=str(policy.id),
        name=policy.name,
        policy_pack=policy.policy_pack,
        rules=dict(policy.rules or {}),
    )
