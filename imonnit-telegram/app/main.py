import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.logging_setup import setup_logging
from app.imap.receiver import receiver_loop
from app.worker.dispatcher import start_worker
from app.worker.scheduler import start_scheduler
from app.api import health, admin

setup_logging()
logger = logging.getLogger(__name__)

background_tasks = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_at_startup()
    
    # Arrancar tareas de fondo
    task_receiver = asyncio.create_task(receiver_loop())
    task_worker = asyncio.create_task(start_worker())
    task_scheduler = asyncio.create_task(start_scheduler())
    
    background_tasks.update([task_receiver, task_worker, task_scheduler])
    
    yield
    
    # Cierre ordenado
    logger.info("Apagando servicios...")
    for t in background_tasks:
        t.cancel()
        
    await asyncio.gather(*background_tasks, return_exceptions=True)
    logger.info("Apagado completado.")

app = FastAPI(title="iMonnit Telegram Bridge (IMAP)", lifespan=lifespan)

app.include_router(health.router)
app.include_router(admin.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
