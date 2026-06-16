from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import Actor, resolve_actor
from modules.core.database import get_session
from modules.core.models import Agent, Post

router = APIRouter(prefix="/integration", tags=["integration"])


@router.get("/health")
async def integration_health():
    return {"status": "ok", "connectors": []}
