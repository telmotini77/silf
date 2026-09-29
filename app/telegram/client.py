import httpx
import asyncio
import logging
from typing import Dict, Optional, Any
from app.config import settings
import json

logger = logging.getLogger(__name__)

class TelegramError(Exception):
    pass

class TelegramPermanentError(TelegramError):
    pass

class TelegramClient:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        # Cuando hay grupo configurado, es el destino operativo del servicio.
        # TELEGRAM_CHAT_ID se conserva como alternativa para conversaciones
        # privadas iniciadas por un usuario con el bot.
        self.chat_id = settings.TELEGRAM_GROUP_ID or settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def _request(self, method: str, data: Dict[str, Any], files: Optional[Dict] = None, parse_mode: str = "HTML") -> str:
        url = f"{self.base_url}/{method}"
        data["chat_id"] = self.chat_id
        if "parse_mode" not in data and parse_mode:
            data["parse_mode"] = parse_mode
            
        for attempt in range(5):
            try:
                if files:
                    resp = await self.client.post(url, data=data, files=files)
                else:
                    resp = await self.client.post(url, data=data)
            except Exception as e:
                # Network error -> transient
                if attempt == 4:
                    raise TelegramError(f"Network error: {str(e)}") from None
                await asyncio.sleep(2 ** attempt)
                continue
                
            if resp.status_code == 200:
                return str(resp.json()["result"]["message_id"])
                
            try:
                resp_data = resp.json()
            except ValueError:
                # Proxies o errores 5xx pueden devolver HTML en vez de JSON.
                resp_data = {}
            err_desc = resp_data.get("description", "")
            
            if resp.status_code == 429:
                retry_after = min(resp_data.get("parameters", {}).get("retry_after", 1), 120)
                logger.warning(f"Telegram 429. Waiting {retry_after}s...")
                await asyncio.sleep(retry_after)
                continue
                
            if resp.status_code in (400, 401, 403, 404, 413):
                if "can't parse entities" in err_desc and parse_mode != "":
                    logger.warning(f"Telegram parsing error. Falling back to plain text. Desc: {err_desc}")
                    # Reintento sin HTML
                    data.pop("parse_mode", None)
                    return await self._request(method, data, files, parse_mode="")
                raise TelegramPermanentError(f"HTTP {resp.status_code}: {err_desc}") from None
                
            # Other errors (500, 502) -> transient
            if attempt == 4:
                raise TelegramError(f"HTTP {resp.status_code}: {err_desc}") from None
            await asyncio.sleep(2 ** attempt)

        # Solo se llega aquí si todos los intentos recibieron HTTP 429.
        raise TelegramError("HTTP 429: rate limit persisted after 5 attempts")

    async def send_message(self, text: str, reply_to: Optional[str] = None) -> str:
        data = {
            "text": text,
            "link_preview_options": json.dumps({"is_disabled": True})
        }
        if reply_to:
            data["reply_parameters"] = json.dumps({
                "message_id": int(reply_to),
                "allow_sending_without_reply": True
            })
        return await self._request("sendMessage", data)

    async def send_document(self, document_bytes: bytes, filename: str, caption: str = "", reply_to: Optional[str] = None) -> str:
        if len(document_bytes) > 50 * 1024 * 1024:
            # File too large
            return await self.send_message(f"⚠️ El archivo <b>{filename}</b> superó los 50MB y no se pudo enviar.", reply_to)
            
        # Caption max 1024
        if len(caption) > 1024:
            caption = caption[:1020] + "..."
            
        data = {"caption": caption}
        if reply_to:
            data["reply_parameters"] = json.dumps({
                "message_id": int(reply_to),
                "allow_sending_without_reply": True
            })
            
        files = {"document": (filename, document_bytes)}
        return await self._request("sendDocument", data, files)

telegram_client = TelegramClient()
