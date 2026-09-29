import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select
from app.db import AsyncSessionLocal
from app.models import Message, MessageStatus
from app.ingest import worker_wakeup_event
from app.worker.delivery import deliver_message
from app.telegram.client import TelegramPermanentError
from app.imap.actions import execute_delivery_actions
from app.config import settings

logger = logging.getLogger(__name__)

WORKER_POLL_SECONDS = 15

async def start_worker():
    logger.info("Iniciando dispatcher...")
    while True:
        try:
            processed_any = False
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    now = datetime.now(timezone.utc)
                    stmt = (
                        select(Message)
                        .where(
                            Message.status.in_([MessageStatus.DETECTED, MessageStatus.RETRY]),
                            (Message.next_attempt_at.is_(None)) | (Message.next_attempt_at <= now),
                            Message.attempts < settings.MAX_ATTEMPTS
                        )
                        .order_by(Message.created_at.asc())
                        .limit(5)
                        .with_for_update(skip_locked=True)
                    )
                    
                    res = await db.execute(stmt)
                    messages = res.scalars().all()
                    
                    for msg in messages:
                        msg.status = MessageStatus.SENDING
                    
                if messages:
                    processed_any = True
                    for msg in messages:
                        async with db.begin():
                            stmt = select(Message).where(Message.id == msg.id).with_for_update()
                            res = await db.execute(stmt)
                            locked_msg = res.scalars().first()
                            
                            locked_msg.attempts += 1
                            try:
                                await deliver_message(db, locked_msg)
                                locked_msg.status = MessageStatus.SENT
                                locked_msg.sent_at = datetime.now(timezone.utc)
                                logger.info(f"Mensaje {locked_msg.uid} entregado a Telegram.")
                                
                                # Acciones opcionales en IMAP (ej. MARK_AS_SEEN)
                                await execute_delivery_actions(locked_msg.uid, locked_msg.folder)
                                
                            except TelegramPermanentError as e:
                                locked_msg.status = MessageStatus.FAILED
                                locked_msg.last_error = str(e)
                                logger.error(f"Falla permanente UID {locked_msg.uid}: {e}")
                            except Exception as e:
                                logger.warning(f"Error procesando UID {locked_msg.uid} (Intento {locked_msg.attempts}): {e}")
                                locked_msg.last_error = str(e)
                                if locked_msg.attempts >= settings.MAX_ATTEMPTS:
                                    locked_msg.status = MessageStatus.FAILED
                                else:
                                    locked_msg.status = MessageStatus.RETRY
                                    delay = min(30 * (2 ** (locked_msg.attempts - 1)), 3600)
                                    locked_msg.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                            
            if not processed_any:
                worker_wakeup_event.clear()
                try:
                    await asyncio.wait_for(worker_wakeup_event.wait(), timeout=WORKER_POLL_SECONDS)
                except asyncio.TimeoutError:
                    pass

        except Exception as e:
            logger.error(f"Error en dispatcher: {e}")
            await asyncio.sleep(5)
