import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Message
from app.config import settings
from app.processing.parser import parse_mime
from app.processing.formatter import build_equivalent
from app.processing.sensor_extract import build_summary
from app.processing.splitter import split_message
from app.processing.renderer import render_to_pdf
from app.telegram.client import telegram_client
from app.imap.fetcher import fetch_raw_standalone

logger = logging.getLogger(__name__)

async def deliver_message(db: AsyncSession, msg: Message):
    delivery = msg.delivery or {}
    reply_to = None
    
    # Obtener el MIME raw
    raw_bytes = msg.raw
    if not raw_bytes:
        raw_bytes = await fetch_raw_standalone(msg.uid, msg.folder)
        if not raw_bytes:
            raise Exception(f"Fallo al descargar MIME del UID {msg.uid}. ¿Fue borrado en Carbonio?")
            
        if settings.CACHE_RAW:
            msg.raw = raw_bytes
            
    parsed = parse_mime(raw_bytes)
    
    # 1. Equivalent Mode
    if settings.TELEGRAM_MODE in ("equivalent", "both"):
        eq_text = build_equivalent(parsed.subject, parsed.sender, parsed.date, parsed.html, parsed.text)
        chunks = split_message(eq_text)
        
        for i, chunk in enumerate(chunks):
            key = f"equivalent:{i}"
            if key not in delivery:
                msg_id = await telegram_client.send_message(chunk, reply_to)
                delivery[key] = msg_id
                if i == 0: reply_to = msg_id
            else:
                if i == 0: reply_to = delivery[key]
                
    # 2. Exact Mode
    if settings.TELEGRAM_MODE in ("exact", "both"):
        key_sum = "summary"
        if key_sum not in delivery:
            sum_text = build_summary(parsed.html, parsed.text)
            header = f"🔔 <b>Asunto:</b> {parsed.subject}\n<b>De:</b> {parsed.sender}\n---\n"
            msg_id = await telegram_client.send_message(header + sum_text, reply_to)
            delivery[key_sum] = msg_id
            if not reply_to: reply_to = msg_id
        else:
            if not reply_to: reply_to = delivery[key_sum]
            
        key_pdf = "pdf"
        if key_pdf not in delivery:
            cids = {a['content_id']: a for a in parsed.attachments if a.get('inline')}
            pdf_bytes = render_to_pdf(parsed.html or parsed.text, cids)
            pdf_id = await telegram_client.send_document(
                pdf_bytes, 
                f"alerta_{msg.uid}.pdf", 
                "Vista exacta", 
                reply_to
            )
            delivery[key_pdf] = pdf_id
            
        key_eml = "eml"
        if key_eml not in delivery:
            eml_id = await telegram_client.send_document(
                raw_bytes,
                f"alerta_{msg.uid}.eml",
                "Correo Original",
                reply_to
            )
            delivery[key_eml] = eml_id
            
    # Adjuntos
    for i, att in enumerate(a for a in parsed.attachments if not a.get('inline')):
        key_att = f"att:{i}"
        if key_att not in delivery:
            att_id = await telegram_client.send_document(
                att['data'],
                att['filename'],
                f"Adjunto: {att['filename']}",
                reply_to
            )
            delivery[key_att] = att_id

    msg.delivery = delivery
