from __future__ import annotations

import hashlib
import json
import secrets
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import Actor, resolve_actor
from modules.core.database import get_session
from modules.core.events.service import emit_event
from modules.core.models import Approval, WebhookEndpoint

router = APIRouter(tags=["notifications"])


class WebhookCreate(BaseModel):
    workspace_id: uuid.UUID
    url: HttpUrl
    event_types: list[str] = Field(default_factory=lambda: ["post.created"])


class WebhookResponse(BaseModel):
    id: str
    secret: str


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


async def deliver_webhooks(session: AsyncSession, event_type: str, payload: dict) -> None:
    workspace_id = payload.get("workspace_id")
    if not workspace_id:
        return
    import uuid

    try:
        ws_id = uuid.UUID(str(workspace_id))
    except ValueError:
        return
    endpoints = (
        await session.execute(
            select(WebhookEndpoint).where(
                WebhookEndpoint.workspace_id == ws_id,
                WebhookEndpoint.is_active.is_(True),
            )
        )
    ).scalars().all()
    body = json.dumps({"type": event_type, "payload": payload})
    async with httpx.AsyncClient(timeout=10.0) as client:
        for endpoint in endpoints:
            if endpoint.event_types and event_type not in endpoint.event_types:
                continue
            try:
                await client.post(str(endpoint.url), content=body, headers={"Content-Type": "application/json"})
            except Exception:
                continue


@router.post("/webhooks", response_model=WebhookResponse)
async def create_webhook(
    body: WebhookCreate,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    secret = secrets.token_urlsafe(32)
    endpoint = WebhookEndpoint(
        workspace_id=body.workspace_id,
        url=str(body.url),
        secret_hash=_hash_secret(secret),
        event_types=body.event_types,
    )
    session.add(endpoint)
    await session.commit()
    return WebhookResponse(id=str(endpoint.id), secret=secret)


class ApprovalCreate(BaseModel):
    workspace_id: uuid.UUID
    action: str
    payload: dict = Field(default_factory=dict)


class ApprovalGrant(BaseModel):
    note: str | None = None


@router.post("/approvals")
async def request_approval(
    body: ApprovalCreate,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    approval = Approval(
        workspace_id=body.workspace_id,
        action=body.action,
        payload=body.payload,
    )
    session.add(approval)
    await session.flush()
    await emit_event(
        session,
        event_type="approval.requested",
        aggregate_type="approval",
        aggregate_id=approval.id,
        payload={"action": approval.action},
    )
    await session.commit()
    return {"id": str(approval.id), "status": approval.status}


@router.post("/approvals/{approval_id}/grant")
async def grant_approval(
    approval_id: uuid.UUID,
    body: ApprovalGrant,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    approval = (
        await session.execute(select(Approval).where(Approval.id == approval_id))
    ).scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval.status = "granted"
    approval.granted_by = actor.id if actor.type == "human" else None
    approval.granted_note = body.note
    await emit_event(
        session,
        event_type="approval.granted",
        aggregate_type="approval",
        aggregate_id=approval.id,
        payload={"action": approval.action, "note": approval.granted_note},
    )
    await session.commit()
    return {"id": str(approval.id), "status": approval.status}
