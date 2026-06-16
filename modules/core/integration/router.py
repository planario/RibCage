from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/integration", tags=["integration"])


@router.get("/health")
async def integration_health():
    return {"status": "ok", "connectors": []}
