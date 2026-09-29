"""Composición de la aplicación y ciclo de vida de sus procesos."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import admin, health
from app.config import settings
from app.db import engine
from app.logging_setup import setup_logging
from app.sources.registry import continuous_source_tasks
from app.worker.dispatcher import start_worker
from app.worker.scheduler import start_scheduler

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    for source in settings.ACTIVE_SOURCES:
        settings.check_source(source)

    tasks = [
        asyncio.create_task(start_worker(), name="delivery-worker"),
        asyncio.create_task(start_scheduler(), name="source-scheduler"),
        *continuous_source_tasks(),
    ]
    logger.info("Application started with sources: %s", ", ".join(settings.ACTIVE_SOURCES))
    try:
        yield
    finally:
        logger.info("Stopping background services")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        from app.telegram.client import telegram_client
        await telegram_client.client.aclose()
        await engine.dispose()
        logger.info("Application stopped")


app = FastAPI(title="Carbonio Telegram Forwarder", version="1.0.0", lifespan=lifespan)
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
