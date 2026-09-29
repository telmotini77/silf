import logging
from typing import Optional, Tuple
from app.imap.connection import get_imap_client, select_folder
from app.config import settings
import email
from email.policy import default as default_policy

logger = logging.getLogger(__name__)

async def fetch_headers(client, uid: int) -> Optional[bytes]:
    """Descarga solo las cabeceras y el tamaño (BODY.PEEK[HEADER]) usando un cliente activo."""
    resp = await client.uid("FETCH", str(uid), "(BODY.PEEK[HEADER] RFC822.SIZE)")
    if resp.result != 'OK':
        logger.error(f"Error fetching headers for UID {uid}: {resp}")
        return None
        
    # Las cabeceras suelen venir en el primer elemento parseado de la respuesta
    for line in resp.lines:
        if type(line) is bytes and not line.startswith(b'* '):
            return line # Esto contiene las cabeceras puras
    return None

async def fetch_raw_standalone(uid: int, folder: str = None) -> Optional[bytes]:
    """Abre una conexión corta y descarga el cuerpo completo de un UID."""
    folder = folder or settings.CARBONIO_FOLDER
    client = None
    try:
        client = await get_imap_client()
        await select_folder(client, folder, readonly=True)
        
        # PEEK es imperativo para no alterar los flags de lectura en IMAP
        resp = await client.uid("FETCH", str(uid), "(BODY.PEEK[])")
        if resp.result != 'OK':
            logger.error(f"Error fetching raw for UID {uid}: {resp}")
            return None
            
        for line in resp.lines:
            # En aioimaplib, el literal de body viene normalmente como bytes puros, sin prefijos `* N FETCH...`
            if type(line) is bytes and not line.startswith(b'* '):
                return line
                
        return None
    except Exception as e:
        logger.error(f"Error en fetch_raw_standalone UID {uid}: {e}")
        return None
    finally:
        if client:
            try:
                await client.logout()
            except:
                pass
