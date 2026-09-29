"""Entrega de correos Carbonio como mensajes de texto de Telegram."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message
from app.processing.formatter import build_equivalent
from app.processing.parser import parse_mime
from app.processing.splitter import split_message
from app.telegram.client import telegram_client


async def deliver_message(db: AsyncSession, msg: Message) -> None:
    """Transcribe un correo a texto; nunca adjunta PDF, EML ni archivos."""
    if msg.raw_type.value != "eml":
        raise ValueError(f"Unsupported message type: {msg.raw_type}")

    parsed = parse_mime(msg.raw)
    text = build_equivalent(
        parsed.subject, parsed.sender, parsed.date, parsed.html, parsed.text
    )

    # Un correo normalmente es un solo mensaje. Si excede el máximo de
    # Telegram, se divide en el mismo hilo sin crear documentos adicionales.
    reply_to = None
    for index, chunk in enumerate(split_message(text)):
        key = f"text:{index}"
        message_id = (msg.delivery or {}).get(key)
        if message_id is None:
            message_id = await telegram_client.send_message(chunk, reply_to)
            # JSONB no rastrea mutaciones en el mismo dict: se asigna una copia
            # y se confirma cada parte para que un reintento no la reenvíe.
            msg.delivery = {**(msg.delivery or {}), key: message_id}
            await db.commit()
        if index == 0:
            reply_to = message_id
