from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core.config import settings
from modules.core.database import get_session
from modules.core.models import Agent, TokenRecord, User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer(auto_error=False)


@dataclass
class Actor:
    id: uuid.UUID
    type: str  # human | agent
    workspace_id: uuid.UUID | None = None
    scopes: list[str] | None = None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(prefix: str = "rbc") -> tuple[str, str, str]:
    raw = f"{prefix}_{secrets.token_urlsafe(32)}"
    return raw, hash_token(raw), raw[:12]


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "type": "human", "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode(
        {"sub": str(user_id), "sid": str(session_id), "type": "refresh", "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


async def resolve_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> Actor:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials

    if token.startswith("rbc_"):
        record = (
            await session.execute(
                select(TokenRecord).where(
                    TokenRecord.token_hash == hash_token(token),
                    TokenRecord.revoked_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        if record.expires_at and record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        record.last_used_at = datetime.now(timezone.utc)
        return Actor(
            id=record.actor_id,
            type=record.actor_type,
            workspace_id=record.workspace_id,
            scopes=list(record.scopes or []),
        )

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "human":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = (await session.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return Actor(id=user.id, type="human")


async def optional_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> Actor | None:
    if not credentials:
        return None
    return await resolve_actor(credentials, session)


def require_scopes(actor: Actor, *scopes: str) -> None:
    if actor.type == "human":
        return
    actor_scopes = set(actor.scopes or [])
    if not all(scope in actor_scopes for scope in scopes):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")


async def get_agent(session: AsyncSession, agent_id: uuid.UUID) -> Agent:
    agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent
