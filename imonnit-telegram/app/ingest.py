import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from app.models import Message, MessageStatus
import email
from email.policy import default as default_policy

logger = logging.getLogger(__name__)

# Evento global para despertar al worker sin hacer polling constante
worker_wakeup_event = asyncio.Event()

async def ingest_email(folder: str, uidvalidity: int, uid: int, raw_headers: bytes):
    """
    Inserta un mensaje de manera idempotente usando ON CONFLICT DO NOTHING.
    Extrae asunto, remitente y message_id de las cabeceras para aplicar filtros.
    No requiere sesión, crea su propia AsyncSessionLocal.
    """
    from app.db import AsyncSessionLocal
    from app.config import settings
    
    status = MessageStatus.DETECTED
    subject = None
    sender = None
    message_id_header = None
    
    try:
        msg_obj = email.message_from_bytes(raw_headers, policy=default_policy)
        subject = str(msg_obj.get("Subject", ""))
        sender = str(msg_obj.get("From", ""))
        message_id_header = str(msg_obj.get("Message-ID", ""))
        
        allowed_senders = settings.allowed_senders_list
        if allowed_senders and not any(s.lower() in sender.lower() for s in allowed_senders):
            status = MessageStatus.IGNORED
            logger.info(f"Ingest {folder}/{uid}: Sender '{sender}' not in ALLOWED_SENDERS")
            
        elif status != MessageStatus.IGNORED:
            keywords = settings.subject_keywords_list
            if keywords and not any(k.lower() in subject.lower() for k in keywords):
                status = MessageStatus.IGNORED
                logger.info(f"Ingest {folder}/{uid}: Subject '{subject}' missing keywords")
                
    except Exception as e:
        logger.error(f"Error parsing headers for {folder}/{uid}: {e}")

    async with AsyncSessionLocal() as db:
        stmt = insert(Message).values(
            folder=folder,
            uidvalidity=uidvalidity,
            uid=uid,
            message_id_header=message_id_header,
            subject=subject,
            sender=sender,
            status=status,
            delivery={}
        )
        
        # Idempotencia: UNIQUE constraint en folder, uidvalidity, uid
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['folder', 'uidvalidity', 'uid']
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        if result.rowcount > 0:
            logger.info(f"Nuevo mensaje detectado: {folder}/{uid} (Status: {status})")
            if status == MessageStatus.DETECTED:
                worker_wakeup_event.set()
        else:
            logger.debug(f"Mensaje duplicado (UID) ignorado: {folder}/{uid}")
