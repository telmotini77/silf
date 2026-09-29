from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import get_db
from app.security import require_admin
from app.models import Message, MessageStatus

router = APIRouter(prefix="/admin/messages", tags=["Admin"], dependencies=[Depends(require_admin)])

@router.get("")
async def list_messages(status: str = None, limit: int = Query(50, le=100), db: AsyncSession = Depends(get_db)):
    stmt = select(Message).order_by(Message.id.desc()).limit(limit)
    if status:
        try:
            enum_status = MessageStatus(status)
            stmt = stmt.where(Message.status == enum_status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
            
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    return [
        {
            "id": m.id,
            "uid": m.uid,
            "folder": m.folder,
            "subject": m.subject,
            "status": m.status,
            "attempts": m.attempts,
            "delivery": m.delivery
        }
        for m in messages
    ]

@router.post("/{message_id}/retry")
async def retry_message(message_id: int, reset: bool = False, db: AsyncSession = Depends(get_db)):
    stmt = select(Message).where(Message.id == message_id)
    result = await db.execute(stmt)
    msg = result.scalars().first()
    
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
        
    msg.status = MessageStatus.RETRY
    msg.next_attempt_at = None
    msg.attempts = 0
    if reset:
        msg.delivery = {}
        
    await db.commit()
    from app.ingest import worker_wakeup_event
    worker_wakeup_event.set()
    
    return {"message": f"Message {message_id} queued for retry."}
