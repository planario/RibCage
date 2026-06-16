from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import Actor, resolve_actor
from modules.core.database import get_session
from modules.core.models import Agent, Post

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.get("/queue")
async def moderation_queue(
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    locked_threads = (
        await session.execute(select(Post).where(Post.is_locked.is_(True)).limit(50))
    ).scalars().all()
    suspended_agents = (
        await session.execute(select(Agent).where(Agent.is_suspended.is_(True)).limit(50))
    ).scalars().all()
    return {
        "locked_threads": [{"id": str(t.id), "title": t.title} for t in locked_threads],
        "suspended_agents": [{"id": str(a.id), "display_name": a.display_name} for a in suspended_agents],
    }
