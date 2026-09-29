from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from app.db import get_db
from app.models import Message, MessageStatus
from app.security import require_admin
from app.ingest import worker_wakeup_event

router = APIRouter(dependencies=[Depends(require_admin)])

@router.get("/messages")
async def list_messages(status: str = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(Message).order_by(Message.created_at.desc()).limit(100)
    if status:
        try:
            enum_status = MessageStatus(status)
            stmt = stmt.where(Message.status == enum_status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Estado inválido")
            
    res = await db.execute(stmt)
    messages = res.scalars().all()
    return [{"id": m.id, "source": m.source, "status": m.status, "attempts": m.attempts} for m in messages]

@router.post("/messages/{id}/retry")
async def retry_message(id: int, reset: bool = Query(False), db: AsyncSession = Depends(get_db)):
    stmt = select(Message).where(Message.id == id)
    res = await db.execute(stmt)
    msg = res.scalars().first()
    
    if not msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
        
    msg.status = MessageStatus.RETRY
    msg.next_attempt_at = None
    msg.last_error = None
    if reset:
        msg.attempts = 0
        msg.delivery = {}
        
    db.add(msg)
    await db.commit()
    worker_wakeup_event.set()
    
    return {"status": "ok", "message": f"Mensaje {id} programado para reintento"}
