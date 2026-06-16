from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.auth import (
    Actor,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    resolve_actor,
)
from modules.core.database import get_session
from modules.core.events.service import emit_event, write_audit
from modules.core.models import Session, User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    display_name: str


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:64]


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    existing = (
        await session.execute(
            select(User).where((User.email == body.email) | (User.username == body.username))
        )
    ).scalar_one_or_none()
    if existing:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Email or username already registered")

    user = User(
        email=body.email,
        username=body.username,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
    )
    session.add(user)
    await session.flush()

    db_session = Session(user_id=user.id, refresh_token_hash="pending")
    session.add(db_session)
    await session.flush()

    refresh = create_refresh_token(user.id, db_session.id)
    db_session.refresh_token_hash = hash_token(refresh)
    access = create_access_token(user.id)

    await write_audit(
        session,
        event_type="user.registered",
        actor_id=user.id,
        actor_type="human",
        payload={"email": user.email},
    )
    await session.commit()
    return AuthResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException

    from modules.core.auth import verify_password

    user = (await session.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    db_session = Session(user_id=user.id, refresh_token_hash="pending")
    session.add(db_session)
    await session.flush()

    refresh = create_refresh_token(user.id, db_session.id)
    db_session.refresh_token_hash = hash_token(refresh)
    access = create_access_token(user.id)
    await session.commit()
    return AuthResponse(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=UserResponse)
async def me(actor: Actor = Depends(resolve_actor), session: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException

    if actor.type != "human":
        raise HTTPException(status_code=403, detail="Agents cannot use /auth/me")
    user = (await session.execute(select(User).where(User.id == actor.id))).scalar_one()
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        display_name=user.display_name,
    )
