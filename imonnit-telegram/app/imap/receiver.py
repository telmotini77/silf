import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Tuple, List

from sqlalchemy.future import select
from aioimaplib import aioimaplib

from app.config import settings
from app.db import AsyncSessionLocal
from app.models import MailboxState
from app.imap.connection import get_imap_client, select_folder, check_capabilities
from app.imap.fetcher import fetch_headers
from app.ingest import ingest_email

logger = logging.getLogger(__name__)

async def get_or_create_state(db) -> MailboxState:
    stmt = select(MailboxState).where(MailboxState.folder == settings.CARBONIO_FOLDER)
    res = await db.execute(stmt)
    state = res.scalars().first()
    if not state:
        state = MailboxState(folder=settings.CARBONIO_FOLDER, uidvalidity=0, last_uid=0)
        db.add(state)
        await db.commit()
        await db.refresh(state)
    return state

async def handle_new_uids(client: aioimaplib.IMAP4_SSL, uids: List[int], folder: str, uidvalidity: int):
    """Procesa UIDs nuevos descargando cabeceras e ingestando en BD."""
    if not uids:
        return
        
    for uid in sorted(uids):
        raw_headers = await fetch_headers(client, uid)
        if raw_headers:
            await ingest_email(folder, uidvalidity, uid, raw_headers)

async def sync_mailbox(client: aioimaplib.IMAP4_SSL, db) -> int:
    """Sincroniza y retorna el nuevo last_uid."""
    state = await get_or_create_state(db)
    uidvalidity, uidnext = await select_folder(client, settings.CARBONIO_FOLDER, readonly=(not settings.MARK_AS_SEEN and not settings.MOVE_TO))
    
    if state.uidvalidity != uidvalidity:
        logger.warning(f"UIDVALIDITY cambió de {state.uidvalidity} a {uidvalidity}. Resincronizando...")
        state.uidvalidity = uidvalidity
        
        if settings.BACKFILL_DAYS > 0:
            date_since = (datetime.now() - timedelta(days=settings.BACKFILL_DAYS)).strftime("%d-%b-%Y")
            search_crit = f'SINCE {date_since}'
        else:
            # Resincronizar últimos 2 días por seguridad
            date_since = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
            search_crit = f'SINCE {date_since}'
            
        resp = await client.search(search_crit)
    else:
        # Búsqueda normal incremental
        if state.last_uid == 0 and uidnext:
            # Si no hay estado, empezamos desde uidnext - 1 a menos que haya backfill
            state.last_uid = max(0, uidnext - 1)
            
        resp = await client.uid("SEARCH", f"UID {state.last_uid + 1}:*")
        
    if resp.result != 'OK':
        logger.error(f"Search failed: {resp}")
        return state.last_uid
        
    # Extraer UIDs numéricos (ignorar strings vacíos o caracteres)
    uids_found = []
    for line in resp.lines:
        for part in line.decode().split():
            if part.isdigit():
                uids_found.append(int(part))
                
    # Filtrar UIDs que ya tenemos (IMAP a veces devuelve el último UID si no hay nuevos con N:*)
    new_uids = [u for u in uids_found if u > state.last_uid]
    
    await handle_new_uids(client, new_uids, settings.CARBONIO_FOLDER, uidvalidity)
    
    if new_uids:
        state.last_uid = max(new_uids)
        
    state.last_idle_at = datetime.now(timezone.utc)
    state.connected = True
    db.add(state)
    await db.commit()
    
    return state.last_uid

async def receiver_loop():
    logger.info("Iniciando IMAP IDLE Receiver...")
    backoff = 1.0
    
    while True:
        client = None
        try:
            client = await get_imap_client()
            caps = await check_capabilities(client)
            
            async with AsyncSessionLocal() as db:
                state = await get_or_create_state(db)
                state.connected = True
                db.add(state)
                await db.commit()
                
            backoff = 1.0 # Reset backoff on successful connect
            
            while True:
                async with AsyncSessionLocal() as db:
                    last_uid = await sync_mailbox(client, db)
                    
                if not caps.get("IDLE"):
                    logger.warning("Servidor no soporta IDLE. Polling cada 30s.")
                    await asyncio.sleep(30)
                    continue
                    
                # Entrar en IDLE
                logger.info("Entrando en IDLE...")
                idle_task = asyncio.create_task(client.idle_start())
                
                # Esperar EXISTS o timeout de IDLE_RENEW_MINUTES
                timeout_sec = settings.IDLE_RENEW_MINUTES * 60
                
                try:
                    # Esperamos notificaciones del servidor asíncronamente
                    # aioimaplib permite iterar o esperar a client.wait_server_push()
                    await asyncio.wait_for(client.wait_server_push(), timeout=timeout_sec)
                    logger.info("Notificación recibida en IDLE, despertando...")
                except asyncio.TimeoutError:
                    logger.debug("IDLE Timeout alcanzado, renovando...")
                
                client.idle_done()
                await idle_task
                
                async with AsyncSessionLocal() as db:
                    state = await get_or_create_state(db)
                    state.last_idle_at = datetime.now(timezone.utc)
                    db.add(state)
                    await db.commit()
                    
        except asyncio.CancelledError:
            logger.info("Receptor IMAP cancelado.")
            if client:
                try:
                    await client.logout()
                except: pass
            break
        except Exception as e:
            logger.error(f"Error en el receptor IMAP: {e}")
            if client:
                try:
                    await client.logout()
                except: pass
                
            # Error de autenticación
            if "AUTHENTICATIONFAILED" in str(e).upper() or "LOGIN" in str(e).upper():
                backoff = 600 # 10 minutos
                logger.error(f"Fallo de auth, backoff agresivo de {backoff}s")
            else:
                backoff = min(300, backoff * 2) # max 5 minutos
                
            sleep_time = backoff + random.uniform(0, 1) # Jitter
            logger.info(f"Reconectando en {sleep_time:.2f} segundos...")
            
            async with AsyncSessionLocal() as db:
                state = await get_or_create_state(db)
                state.connected = False
                db.add(state)
                await db.commit()
                
            await asyncio.sleep(sleep_time)
