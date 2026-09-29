"""Recupera mensajes abandonados por una interrupción del proceso."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, update

from app.db import AsyncSessionLocal
from app.models import Message, MessageStatus
from app.worker.dispatcher import MAX_ATTEMPTS

logger = logging.getLogger(__name__)


async def recover_stuck_messages() -> int:
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(minutes=10)
    abandoned = and_(Message.status == MessageStatus.SENDING, Message.updated_at < threshold)
    exhausted = Message.attempts >= MAX_ATTEMPTS
    async with AsyncSessionLocal() as db:
        # El dispatcher ignora los mensajes que agotaron sus intentos; si
        # volvieran a RETRY quedarían en la cola para siempre.
        failed = await db.execute(
            update(Message)
            .where(or_(abandoned, Message.status == MessageStatus.RETRY), exhausted)
            .values(
                status=MessageStatus.FAILED,
                last_error=func.coalesce(Message.last_error, "Delivery interrupted after max attempts"),
            )
        )
        recovered = await db.execute(
            update(Message)
            .where(abandoned, ~exhausted)
            .values(status=MessageStatus.RETRY, next_attempt_at=now)
        )
        await db.commit()
    if failed.rowcount:
        logger.error("Marked %s exhausted message(s) as failed", failed.rowcount)
    if recovered.rowcount:
        logger.warning("Recovered %s abandoned message(s)", recovered.rowcount)
    return recovered.rowcount or 0


async def scheduler_loop() -> None:
    while True:
        try:
            await recover_stuck_messages()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduler cycle failed")
        await asyncio.sleep(300)


async def start_scheduler() -> None:
    await scheduler_loop()
