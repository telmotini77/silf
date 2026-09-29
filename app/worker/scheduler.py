"""Recupera mensajes abandonados por una interrupción del proceso."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.db import AsyncSessionLocal
from app.models import Message, MessageStatus

logger = logging.getLogger(__name__)


async def recover_stuck_messages() -> int:
    threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Message)
            .where(Message.status == MessageStatus.SENDING, Message.updated_at < threshold)
            .values(status=MessageStatus.RETRY, next_attempt_at=datetime.now(timezone.utc))
        )
        await db.commit()
    if result.rowcount:
        logger.warning("Recovered %s abandoned message(s)", result.rowcount)
    return result.rowcount or 0


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
