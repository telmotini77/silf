from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from app.db import get_db
from app.models import MailboxState
from app.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(MailboxState).where(MailboxState.folder == settings.CARBONIO_FOLDER)
        result = await db.execute(stmt)
        state = result.scalars().first()
        
        db_ok = True
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")
        
    if not state:
        return {"status": "ok", "db": "connected", "imap": "initializing"}
        
    now = datetime.now(timezone.utc)
    # Tolerancia de 30 minutos desde el último IDLE registrado
    idle_healthy = state.last_idle_at and (now - state.last_idle_at).total_seconds() < 1800
    
    if not state.connected or not idle_healthy:
        raise HTTPException(
            status_code=503, 
            detail={
                "status": "error",
                "connected": state.connected,
                "last_idle_at": state.last_idle_at,
                "last_uid": state.last_uid
            }
        )
        
    return {
        "status": "ok",
        "connected": True,
        "last_idle_at": state.last_idle_at,
        "last_uid": state.last_uid
    }
