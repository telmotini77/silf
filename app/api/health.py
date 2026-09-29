from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.db import AsyncSessionLocal

router = APIRouter()


@router.get("/")
async def liveness() -> dict[str, str]:
    """El proceso HTTP está vivo."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness() -> dict[str, str]:
    """El proceso puede comunicarse con su cola persistente."""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from error
    return {"status": "ready"}
