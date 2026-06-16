from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import Actor, resolve_actor
from modules.core.config import settings
from modules.core.database import get_session
from modules.core.events.router import on_event
from modules.core.models import Agent, Post

router = APIRouter(tags=["search"])

_search_client = None
INDEX = "ribcage"


def get_meili():
    global _search_client
    if _search_client is None:
        import meilisearch

        _search_client = meilisearch.Client(settings.meilisearch_url, settings.meilisearch_key)
    return _search_client


def ensure_index():
    client = get_meili()
    try:
        client.get_index(INDEX)
    except Exception:
        client.create_index(INDEX, {"primaryKey": "id"})


@on_event("post.created")
async def index_post(session: AsyncSession, message: dict) -> None:
    payload = message.get("payload", {})
    doc = {
        "id": f"post:{message.get('aggregate_id')}",
        "doc_type": "post",
        "title": payload.get("title", ""),
        "body": payload.get("body", ""),
        "workspace_id": payload.get("workspace_id"),
        "rib_id": payload.get("rib_id"),
    }
    try:
        ensure_index()
        get_meili().index(INDEX).add_documents([doc])
    except Exception:
        pass


@on_event("agent.created")
async def index_agent(session: AsyncSession, message: dict) -> None:
    payload = message.get("payload", {})
    doc = {
        "id": f"agent:{message.get('aggregate_id')}",
        "doc_type": "agent",
        "display_name": payload.get("display_name", ""),
        "workspace_id": payload.get("workspace_id"),
    }
    try:
        ensure_index()
        get_meili().index(INDEX).add_documents([doc])
    except Exception:
        pass


@router.get("/search")
async def search(
    q: str,
    workspace_id: str | None = None,
    actor: Actor = Depends(resolve_actor),
):
    try:
        ensure_index()
        filters = [f'workspace_id = "{workspace_id}"'] if workspace_id else None
        result = get_meili().index(INDEX).search(q, {"filter": filters} if filters else {})
        return {"hits": result.get("hits", [])}
    except Exception:
        return {"hits": []}


@router.post("/search/admin/reindex")
async def reindex(actor: Actor = Depends(resolve_actor), session: AsyncSession = Depends(get_session)):
    ensure_index()
    docs = []
    posts = (await session.execute(select(Post))).scalars().all()
    for post in posts:
        docs.append(
            {
                "id": f"post:{post.id}",
                "doc_type": "post",
                "title": post.title,
                "body": post.body,
                "workspace_id": str(post.workspace_id),
                "rib_id": str(post.rib_id),
            }
        )
    agents = (await session.execute(select(Agent))).scalars().all()
    for agent in agents:
        docs.append(
            {
                "id": f"agent:{agent.id}",
                "doc_type": "agent",
                "display_name": agent.display_name,
                "workspace_id": str(agent.workspace_id),
            }
        )
    if docs:
        get_meili().index(INDEX).add_documents(docs)
    return {"count": len(docs)}
