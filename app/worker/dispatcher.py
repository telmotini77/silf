"""Consumidor de la cola persistente.

El bloqueo de PostgreSQL solo se conserva al reclamar un mensaje. La llamada a
Telegram ocurre fuera de toda transacción para no bloquear al resto de workers.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from app.db import AsyncSessionLocal
from app.ingest import worker_wakeup_event
from app.models import Message, MessageStatus
from app.telegram.client import TelegramPermanentError
from app.worker.delivery import deliver_message

logger = logging.getLogger(__name__)

WORKER_POLL_SECONDS = 15
MAX_ATTEMPTS = 8
BATCH_SIZE = 5


async def claim_messages() -> list[int]:
    """Reclama una tanda corta sin conservar el lock durante la entrega."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(
                select(Message)
                .where(
                    Message.status.in_([MessageStatus.RECEIVED, MessageStatus.RETRY]),
                    or_(Message.next_attempt_at.is_(None), Message.next_attempt_at <= now),
                    Message.attempts < MAX_ATTEMPTS,
                )
                .order_by(Message.created_at.asc())
                .limit(BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            messages = result.scalars().all()
            for message in messages:
                message.status = MessageStatus.SENDING
                message.attempts += 1
                message.next_attempt_at = None
            return [message.id for message in messages]


async def process_message(message_id: int) -> None:
    """Entrega un mensaje reclamado y registra un resultado duradero."""
    async with AsyncSessionLocal() as db:
        message = await db.get(Message, message_id)
        if message is None or message.status != MessageStatus.SENDING:
            return
        try:
            await deliver_message(db, message)
            message.status = MessageStatus.SENT
            message.sent_at = datetime.now(timezone.utc)
            message.last_error = None
            logger.info("Message %s delivered", message.id)
        except TelegramPermanentError as error:
            message.status = MessageStatus.FAILED
            message.last_error = str(error)
            logger.error("Message %s failed permanently: %s", message.id, error)
        except Exception as error:
            message.last_error = str(error)
            if message.attempts >= MAX_ATTEMPTS:
                message.status = MessageStatus.FAILED
            else:
                delay = min(30 * 2 ** (message.attempts - 1), 3600)
                message.status = MessageStatus.RETRY
                message.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            logger.warning("Message %s delivery failed: %s", message.id, error)
        await db.commit()


async def dispatcher_loop() -> None:
    logger.info("Dispatcher started")
    while True:
        try:
            # Clear before querying: an ingestion that races with this cycle either
            # appears in the query or leaves the event set for the wait below.
            worker_wakeup_event.clear()
            message_ids = await claim_messages()
            if message_ids:
                for message_id in message_ids:
                    await process_message(message_id)
                continue
            try:
                await asyncio.wait_for(worker_wakeup_event.wait(), timeout=WORKER_POLL_SECONDS)
            except asyncio.TimeoutError:
                pass
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Dispatcher loop failed")
            await asyncio.sleep(5)


async def start_worker() -> None:
    await dispatcher_loop()
