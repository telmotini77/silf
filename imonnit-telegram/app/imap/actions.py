import logging
from app.imap.connection import get_imap_client, select_folder, check_capabilities
from app.config import settings

logger = logging.getLogger(__name__)

async def execute_delivery_actions(uid: int, folder: str = None):
    """Ejecuta acciones configuradas sobre un mensaje después de enviarlo (ej. MARK_AS_SEEN)."""
    folder = folder or settings.CARBONIO_FOLDER
    
    if not settings.MARK_AS_SEEN and not settings.MOVE_TO:
        return
        
    client = None
    try:
        client = await get_imap_client()
        # Necesita modo RW
        await select_folder(client, folder, readonly=False)
        
        if settings.MARK_AS_SEEN:
            logger.info(f"Marcando UID {uid} como leído (\\Seen)")
            await client.uid("STORE", str(uid), "+FLAGS", "(\\Seen)")
            
        if settings.MOVE_TO:
            caps = await check_capabilities(client)
            dest = f'"{settings.MOVE_TO}"'
            
            logger.info(f"Moviendo UID {uid} a {dest}")
            if caps.get("MOVE"):
                await client.uid("MOVE", str(uid), dest)
            else:
                # Fallback: COPY + STORE + EXPUNGE
                res = await client.uid("COPY", str(uid), dest)
                if res.result == 'OK':
                    await client.uid("STORE", str(uid), "+FLAGS", "(\\Deleted)")
                    if caps.get("UIDPLUS"):
                        await client.uid("EXPUNGE", str(uid))
                    else:
                        logger.warning("Servidor no soporta UIDPLUS, no se pudo hacer UID EXPUNGE. Se usará EXPUNGE normal.")
                        await client.expunge()
                else:
                    logger.error(f"Fallo al copiar UID {uid} a {dest}: {res}")
                    
    except Exception as e:
        logger.error(f"Error en execute_delivery_actions UID {uid}: {e}")
    finally:
        if client:
            try:
                await client.logout()
            except:
                pass
