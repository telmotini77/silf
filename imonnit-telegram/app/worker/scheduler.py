import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import update
from sqlalchemy.future import select
from app.db import AsyncSessionLocal
from app.models import Message, MessageStatus, MailboxState
from app.config import settings

logger = logging.getLogger(__name__)

async def start_scheduler():
    logger.info("Iniciando scheduler (cada 5 min)...")
    while True:
        await asyncio.sleep(300)
        try:
            logger.info("Ejecutando reconciliación y limpieza...")
            
            async with AsyncSessionLocal() as db:
                # 1. Recuperar mensajes atascados en SENDING > 10 min
                ten_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
                stmt_stuck = (
                    update(Message)
                    .where(
                        Message.status == MessageStatus.SENDING,
                        Message.updated_at < ten_mins_ago
                    )
                    .values(
                        status=MessageStatus.RETRY,
                        next_attempt_at=datetime.now(timezone.utc)
                    )
                )
                res = await db.execute(stmt_stuck)
                await db.commit()
                if res.rowcount > 0:
                    logger.warning(f"Se devolvieron {res.rowcount} mensajes atascados a la cola.")
                    
                # 2. Reconciliación IMAP por si se perdió un EXISTS
                # Esto se hace desde la BD viendo last_uid, y si faltan, forzamos la sincronización.
                # Como sync_mailbox usa get_imap_client, lo llamaremos importándolo.
                # Para evitar dependencias circulares complejas, usaremos un cliente corto aquí.
                from app.imap.connection import get_imap_client
                from app.imap.receiver import sync_mailbox
                
                try:
                    client = await get_imap_client()
                    await sync_mailbox(client, db)
                    await client.logout()
                except Exception as e:
                    logger.error(f"Fallo en reconciliación IMAP del scheduler: {e}")
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error en scheduler: {e}")
