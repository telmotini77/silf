import ssl
import logging
from aioimaplib import aioimaplib
from app.config import settings

logger = logging.getLogger(__name__)

async def get_imap_client() -> aioimaplib.IMAP4_SSL:
    """Crea y conecta un cliente IMAP de forma segura."""
    ssl_context = ssl.create_default_context()
    if settings.CARBONIO_CA_FILE:
        ssl_context.load_verify_locations(cafile=settings.CARBONIO_CA_FILE)
        
    client = aioimaplib.IMAP4_SSL(
        host=settings.CARBONIO_HOST,
        port=settings.CARBONIO_PORT,
        ssl_context=ssl_context,
        timeout=30.0
    )
    
    await client.wait_hello_from_server()
    
    login_resp = await client.login(settings.CARBONIO_USER, settings.CARBONIO_PASSWORD)
    if login_resp.result != 'OK':
        raise Exception(f"IMAP Login failed: {login_resp}")
        
    return client

async def check_capabilities(client: aioimaplib.IMAP4_SSL) -> dict:
    resp = await client.capability()
    caps = resp.lines[0].decode().upper()
    return {
        "IDLE": "IDLE" in caps,
        "UIDPLUS": "UIDPLUS" in caps,
        "MOVE": "MOVE" in caps
    }

async def select_folder(client: aioimaplib.IMAP4_SSL, folder: str, readonly: bool = True):
    if readonly:
        resp = await client.examine(f'"{folder}"')
    else:
        resp = await client.select(f'"{folder}"')
        
    if resp.result != 'OK':
        raise Exception(f"IMAP Select/Examine failed for folder {folder}: {resp}")
        
    # Extraer UIDVALIDITY y UIDNEXT de los headers (resp.lines)
    uidvalidity = None
    uidnext = None
    for line in resp.lines:
        line_str = line.decode().upper()
        if "UIDVALIDITY" in line_str:
            parts = line_str.split("UIDVALIDITY", 1)[1]
            # Formato: [UIDVALIDITY 12345]
            uidvalidity = int(parts.strip(" ]").split()[0])
        elif "UIDNEXT" in line_str:
            parts = line_str.split("UIDNEXT", 1)[1]
            uidnext = int(parts.strip(" ]").split()[0])
            
    return uidvalidity, uidnext
