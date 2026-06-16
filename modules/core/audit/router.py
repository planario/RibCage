from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import Actor, resolve_actor
from modules.core.database import get_session
from modules.core.models import AuditRecord

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditItem(BaseModel):
    id: str
    event_type: str
    actor_id: str | None
    actor_type: str | None
    resource_type: str | None
    payload: dict
    created_at: str


class AuditListResponse(BaseModel):
    items: list[AuditItem]


@router.get("/events", response_model=AuditListResponse)
async def list_audit_events(
    workspace_id: uuid.UUID,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    records = (
        await session.execute(
            select(AuditRecord)
            .where(AuditRecord.workspace_id == workspace_id)
            .order_by(AuditRecord.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    return AuditListResponse(
        items=[
            AuditItem(
                id=str(r.id),
                event_type=r.event_type,
                actor_id=str(r.actor_id) if r.actor_id else None,
                actor_type=r.actor_type,
                resource_type=r.resource_type,
                payload=dict(r.payload or {}),
                created_at=r.created_at.isoformat(),
            )
            for r in records
        ]
    )
