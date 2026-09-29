import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from app.models import Message, MessageStatus, RawType
import email
from email.policy import default as default_policy

logger = logging.getLogger(__name__)

# Evento global para despertar al worker sin hacer polling constante
worker_wakeup_event = asyncio.Event()

class Ingestor:
    @staticmethod
    async def exists(db: AsyncSession, source: str, provider_id: str) -> bool:
        stmt = select(Message.id).where(Message.source == source, Message.provider_id == provider_id)
        res = await db.execute(stmt)
        return res.first() is not None

    @staticmethod
    async def ingest(db: AsyncSession, source: str, provider_id: str, raw: bytes, raw_type: RawType) -> bool:
        """
        Inserta un mensaje de manera idempotente usando ON CONFLICT DO NOTHING.
        Extrae asunto, remitente y message_id de las cabeceras si es EML.
        Retorna True si fue insertado y no ignorado.
        """
        status = MessageStatus.RECEIVED
        subject = None
        sender = None
        message_id_header = None
        
        # Parse headers if EML to apply filters
        if raw_type == RawType.EML:
            try:
                # Usar BytesHeaderParser sería ideal, aquí usamos email.message_from_bytes para sacar cabeceras
                msg_obj = email.message_from_bytes(raw, policy=default_policy)
                subject = str(msg_obj.get("Subject", ""))
                sender = str(msg_obj.get("From", ""))
                message_id_header = str(msg_obj.get("Message-ID", ""))
                
                # Apply filters
                from app.config import settings
                
                # Check sender
                allowed_senders = settings.allowed_senders_list
                if allowed_senders and not any(s.lower() in sender.lower() for s in allowed_senders):
                    status = MessageStatus.IGNORED
                    logger.info(f"Ingest {provider_id}: Sender '{sender}' not in ALLOWED_SENDERS")
                    
                # Check subject keywords (only if not already ignored and keywords exist)
                elif status != MessageStatus.IGNORED:
                    keywords = settings.subject_keywords_list
                    if keywords and not any(k.lower() in subject.lower() for k in keywords):
                        status = MessageStatus.IGNORED
                        logger.info(f"Ingest {provider_id}: Subject '{subject}' missing keywords")
                        
            except Exception as e:
                logger.error(f"Error parsing EML headers for {provider_id}: {e}")

        stmt = insert(Message).values(
            source=source,
            provider_id=provider_id,
            raw=raw,
            raw_type=raw_type,
            subject=subject,
            sender=sender,
            message_id_header=message_id_header,
            status=status,
            delivery={}
        )
        
        # Idempotencia: ON CONFLICT DO NOTHING
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['source', 'provider_id']
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        # rowcount > 0 indica que realmente se insertó un nuevo registro
        if result.rowcount > 0:
            logger.info(f"Nuevo mensaje ingresado: {source}/{provider_id} (Status: {status})")
            if status == MessageStatus.RECEIVED:
                worker_wakeup_event.set()
                return True
        else:
            logger.debug(f"Mensaje duplicado ignorado: {source}/{provider_id}")
            
        return False
