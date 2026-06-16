from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import Actor, require_scopes, resolve_actor
from modules.core.database import get_session
from modules.core.events.service import emit_event, write_audit
from modules.core.models import Comment, Post, Rib

router = APIRouter(tags=["threads"])


class AuthorInfo(BaseModel):
    id: str
    type: str


class PostResponse(BaseModel):
    id: str
    rib_id: str
    title: str
    body: str
    post_type: str
    status: str
    is_pinned: bool
    labels: list[str]
    author: AuthorInfo
    created_at: str
    comment_count: int


class CommentResponse(BaseModel):
    id: str
    body: str
    author: AuthorInfo
    parent_id: str | None
    created_at: str


class FeedResponse(BaseModel):
    items: list[PostResponse]
    next_cursor: str | None = None


class ThreadResponse(BaseModel):
    post: PostResponse
    comments: list[CommentResponse]


class CreatePostRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(min_length=1)
    post_type: str = "discussion"


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1)
    parent_id: uuid.UUID | None = None


class StatusTransitionRequest(BaseModel):
    status: str


def _post_to_response(post: Post, comment_count: int = 0) -> PostResponse:
    return PostResponse(
        id=str(post.id),
        rib_id=str(post.rib_id),
        title=post.title,
        body=post.body,
        post_type=post.post_type,
        status=post.status,
        is_pinned=post.is_pinned,
        labels=list(post.labels or []),
        author=AuthorInfo(id=str(post.author_id), type=post.author_type),
        created_at=post.created_at.isoformat(),
        comment_count=comment_count,
    )


@router.get("/ribs/{rib_id}/feed", response_model=FeedResponse)
async def get_feed(
    rib_id: uuid.UUID,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    posts = (
        await session.execute(
            select(Post).where(Post.rib_id == rib_id).order_by(Post.created_at.desc()).limit(50)
        )
    ).scalars().all()
    items = []
    for post in posts:
        count = (
            await session.execute(select(func.count()).select_from(Comment).where(Comment.post_id == post.id))
        ).scalar_one()
        items.append(_post_to_response(post, count))
    return FeedResponse(items=items)


@router.post("/ribs/{rib_id}/posts", response_model=PostResponse)
async def create_post(
    rib_id: uuid.UUID,
    body: CreatePostRequest,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    require_scopes(actor, "write:post")
    rib = (await session.execute(select(Rib).where(Rib.id == rib_id))).scalar_one_or_none()
    if not rib:
        raise HTTPException(status_code=404, detail="Rib not found")
    if rib.is_locked:
        raise HTTPException(status_code=403, detail="Rib is locked")

    post = Post(
        rib_id=rib.id,
        workspace_id=rib.workspace_id,
        author_type=actor.type,
        author_id=actor.id,
        title=body.title,
        body=body.body,
        post_type=body.post_type,
    )
    session.add(post)
    await session.flush()

    await emit_event(
        session,
        event_type="post.created",
        aggregate_type="post",
        aggregate_id=post.id,
        payload={
            "title": post.title,
            "body": post.body,
            "rib_id": str(post.rib_id),
            "workspace_id": str(post.workspace_id),
            "status": post.status,
            "post_type": post.post_type,
        },
    )
    await write_audit(
        session,
        event_type="post.created",
        workspace_id=post.workspace_id,
        actor_id=actor.id,
        actor_type=actor.type,
        resource_type="post",
        resource_id=post.id,
        payload={"title": post.title, "rib_id": str(post.rib_id)},
    )
    await session.commit()
    return _post_to_response(post, 0)


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: uuid.UUID,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    post = (await session.execute(select(Post).where(Post.id == thread_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Thread not found")
    comments = (
        await session.execute(
            select(Comment).where(Comment.post_id == thread_id).order_by(Comment.created_at)
        )
    ).scalars().all()
    return ThreadResponse(
        post=_post_to_response(post, len(comments)),
        comments=[
            CommentResponse(
                id=str(c.id),
                body=c.body,
                author=AuthorInfo(id=str(c.author_id), type=c.author_type),
                parent_id=str(c.parent_id) if c.parent_id else None,
                created_at=c.created_at.isoformat(),
            )
            for c in comments
        ],
    )


@router.get("/threads/{thread_id}/timeline")
async def get_timeline(
    thread_id: uuid.UUID,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    from modules.core.models import OutboxEvent

    post = (await session.execute(select(Post).where(Post.id == thread_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Thread not found")

    events = (
        await session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.aggregate_id == thread_id)
            .order_by(OutboxEvent.created_at)
        )
    ).scalars().all()
    status_history = [{"status": post.status, "changed_at": post.created_at.isoformat()}]
    return {
        "events": [
            {"type": e.event_type, "payload": e.payload, "created_at": e.created_at.isoformat()}
            for e in events
        ],
        "status_history": status_history,
    }


@router.post("/threads/{thread_id}/comments", response_model=CommentResponse)
async def create_comment(
    thread_id: uuid.UUID,
    body: CreateCommentRequest,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    require_scopes(actor, "write:post")
    post = (await session.execute(select(Post).where(Post.id == thread_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Thread not found")
    if post.is_locked:
        raise HTTPException(status_code=403, detail="Thread is locked")

    comment = Comment(
        post_id=post.id,
        author_type=actor.type,
        author_id=actor.id,
        body=body.body,
        parent_id=body.parent_id,
    )
    session.add(comment)
    await session.flush()

    await emit_event(
        session,
        event_type="comment.created",
        aggregate_type="comment",
        aggregate_id=comment.id,
        payload={"post_id": str(post.id), "body": comment.body, "workspace_id": str(post.workspace_id)},
    )
    await session.commit()
    return CommentResponse(
        id=str(comment.id),
        body=comment.body,
        author=AuthorInfo(id=str(comment.author_id), type=comment.author_type),
        parent_id=str(comment.parent_id) if comment.parent_id else None,
        created_at=comment.created_at.isoformat(),
    )


@router.post("/threads/{thread_id}/status-transitions", response_model=PostResponse)
async def change_status(
    thread_id: uuid.UUID,
    body: StatusTransitionRequest,
    actor: Actor = Depends(resolve_actor),
    session: AsyncSession = Depends(get_session),
):
    post = (await session.execute(select(Post).where(Post.id == thread_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Thread not found")

    old_status = post.status
    post.status = body.status
    await emit_event(
        session,
        event_type="thread.status.changed",
        aggregate_type="post",
        aggregate_id=post.id,
        payload={"from": old_status, "to": body.status, "workspace_id": str(post.workspace_id)},
    )
    await session.commit()
    count = (
        await session.execute(select(func.count()).select_from(Comment).where(Comment.post_id == post.id))
    ).scalar_one()
    return _post_to_response(post, count)
