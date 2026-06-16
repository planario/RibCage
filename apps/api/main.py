import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response
from sqlalchemy import text

from modules.core.agent.router import router as agent_router
from modules.core.audit.router import router as audit_router
from modules.core.config import settings
from modules.core.database import async_session_factory, engine
from modules.core.events.router import outbox_publisher_loop, router as stream_router
from modules.core.identity.router import router as auth_router
from modules.core.integration.router import router as integration_router
from modules.core.moderation.router import router as moderation_router
from modules.core.models import Base
from modules.core.notification.router import router as notification_router
from modules.core.policy.router import router as policy_router
from modules.core.provisioning.router import router as provisioning_router
import modules.core.search.router  # noqa: F401 — register search event handlers
from modules.core.search.router import router as search_router
import modules.core.notification.router  # noqa: F401 — register notification handlers
from modules.core.thread.router import router as thread_router
from modules.core.workspace.router import router as workspace_router

_publisher_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _publisher_task
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _publisher_task = asyncio.create_task(outbox_publisher_loop())
    yield
    if _publisher_task:
        _publisher_task.cancel()


app = FastAPI(
    title="Ribcage API",
    version="1.0.0",
    description="Modular collaboration platform for AI agents and humans",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = FastAPI()
app.mount("/api/v1", api)

api.include_router(auth_router)
api.include_router(workspace_router)
api.include_router(thread_router)
api.include_router(agent_router)
api.include_router(provisioning_router)
api.include_router(policy_router)
api.include_router(audit_router)
api.include_router(search_router)
api.include_router(notification_router)
api.include_router(integration_router)
api.include_router(moderation_router)
api.include_router(stream_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        return Response(
            content=f'{{"status":"not_ready","error":"{str(e)}"}}',
            status_code=503,
            media_type="application/json",
        )


@app.get("/metrics")
async def metrics():
    if not settings.prometheus_enabled:
        return {"enabled": False}
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
