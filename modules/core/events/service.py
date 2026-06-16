from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.models import AuditRecord, OutboxEvent, utcnow


async def emit_event(
    session: AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    payload: dict,
) -> None:
    session.add(
        OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
        )
    )


async def write_audit(
    session: AsyncSession,
    *,
    event_type: str,
    workspace_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    actor_type: str | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> None:
    session.add(
        AuditRecord(
            workspace_id=workspace_id,
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload or {},
            created_at=utcnow(),
        )
    )
