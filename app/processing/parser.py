import email
from email import policy
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class ParsedEmail:
    subject: str
    sender: str
    date: str
    message_id: str
    html: str
    text: str
    attachments: List[Dict]

def parse_mime(raw_bytes: bytes) -> ParsedEmail:
    msg = email.message_from_bytes(raw_bytes, policy=policy.default)
    
    subject = str(msg.get("Subject", ""))
    sender = str(msg.get("From", ""))
    date = str(msg.get("Date", ""))
    message_id = str(msg.get("Message-ID", ""))
    
    html_content = ""
    text_content = ""
    
    # get_body() prioritizes 'html' or 'plain' based on preference
    body_html = msg.get_body(preferencelist=('html',))
    if body_html:
        try:
            html_content = body_html.get_content()
        except LookupError:
            # Tolerancia a charsets inválidos
            payload = body_html.get_payload(decode=True)
            charset = body_html.get_param('charset', 'utf-8')
            html_content = payload.decode(charset, errors="replace") if payload else ""
            
    body_plain = msg.get_body(preferencelist=('plain',))
    if body_plain:
        try:
            text_content = body_plain.get_content()
        except LookupError:
            payload = body_plain.get_payload(decode=True)
            charset = body_plain.get_param('charset', 'utf-8')
            text_content = payload.decode(charset, errors="replace") if payload else ""
            
    attachments = []
    
    for part in msg.walk():
        if part.is_multipart() or part.get_content_type() in ["text/plain", "text/html"]:
            continue
            
        disposition = str(part.get("Content-Disposition", ""))
        content_id = part.get("Content-Id")
        filename = part.get_filename()
        content_type = part.get_content_type()
        
        # Strip brackets from CID
        if content_id and content_id.startswith("<") and content_id.endswith(">"):
            content_id = content_id[1:-1]
            
        is_inline = ("inline" in disposition) or bool(content_id) or ("image" in content_type)
        
        data = part.get_payload(decode=True)
        if data:
            attachments.append({
                "filename": filename or f"file.{content_type.split('/')[-1]}",
                "content_type": content_type,
                "data": data,
                "content_id": content_id,
                "inline": is_inline
            })
            
    return ParsedEmail(
        subject=subject,
        sender=sender,
        date=date,
        message_id=message_id,
        html=html_content,
        text=text_content,
        attachments=attachments
    )
