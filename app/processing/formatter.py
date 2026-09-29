import nh3
from bs4 import BeautifulSoup
import pytz
from email.utils import parseaddr
from html import escape
from app.config import settings

def clean_html(html_str: str) -> str:
    """Remueve etiquetas y atributos no deseados usando nh3 y bs4."""
    # 1. Eliminar nodos que no necesitamos usando BS4
    soup = BeautifulSoup(html_str, 'lxml')
    # Detectar clases ocultas declaradas en hojas de estilo antes de eliminar
    # las etiquetas <style> (los preheaders de correo suelen usar este patrón).
    import re
    hidden_classes = set()
    for style in soup.find_all("style"):
        hidden_classes.update(re.findall(
            r"\.([\w-]+)\s*\{[^}]*?(?:display\s*:\s*none|visibility\s*:\s*hidden)",
            style.get_text(" "),
            flags=re.IGNORECASE,
        ))
    for tag in soup(["script", "style", "head", "title", "meta", "svg", "form"]):
        tag.decompose()
        
    # Eliminar elementos ocultos
    for tag in soup.find_all(lambda t: t.has_attr('hidden') or 
                             ('display' in t.get('style', '') and 'none' in t.get('style', '')) or 
                             ('visibility' in t.get('style', '') and 'hidden' in t.get('style', '')) or
                             hidden_classes.intersection(t.get('class', []))):
        tag.decompose()
        
    # Reemplazar h1-h6 -> b
    for i in range(1, 7):
        for tag in soup.find_all(f'h{i}'):
            tag.name = 'b'
            
    # Listas
    for li in soup.find_all('li'):
        li.insert_before("• ")
        li.unwrap()
        
    # Saltos de línea
    for br in soup.find_all('br'):
        br.replace_with("\n")
    for hr in soup.find_all('hr'):
        hr.replace_with("\n---\n")

    # Tablas
    for table in soup.find_all('table'):
        table_nodes = []
        for row in table.find_all('tr', recursive=False):
            cells = row.find_all(['td', 'th'], recursive=False)
            if len(cells) == 2 and len(cells[0].get_text(strip=True)) < 30:
                # 2 celdas cortas -> Etiqueta: valor
                label = cells[0].get_text(strip=True).rstrip(":")
                bold = soup.new_tag("b")
                bold.string = f"{label}:"
                table_nodes.extend([bold, f" {cells[1].get_text(strip=True)}", "\n"])
            elif len(cells) == 1:
                table_nodes.extend([cells[0].get_text(strip=True), "\n"])
            elif len(cells) > 2:
                table_nodes.extend([" | ".join(c.get_text(strip=True) for c in cells), "\n"])
        table.replace_with(*table_nodes)

    # Reemplazar imagenes por nada
    for img in soup.find_all('img'):
        img.decompose()
        
    # Enlaces: solo http, https y mailto
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if not href.startswith(('http://', 'https://', 'mailto:')):
            a.unwrap()

    # Obtener el texto reconstruido
    raw_text = str(soup)
    
    # 2. Pasada final estricta con nh3
    ALLOWED_TAGS = {'b', 'strong', 'i', 'em', 'u', 's', 'del', 'strike', 'a', 'code', 'pre', 'blockquote'}
    ALLOWED_ATTRS = {'a': {'href'}, 'code': {'class'}}
    
    final_html = nh3.clean(raw_text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
    
    # Normalizar saltos de línea (máximo dos seguidos)
    final_html = re.sub(r'\n{3,}', '\n\n', final_html)
    
    return final_html.strip()

def build_equivalent(subject: str, sender: str, date_str: str, html_body: str, text_body: str) -> str:
    """Construye una ficha de correo clara y legible para Telegram."""
    # Convertir zona horaria
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        local_tz = pytz.timezone(settings.TIMEZONE)
        local_dt = dt.astimezone(local_tz)
        formatted_date = local_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        formatted_date = date_str

    display_name, email_address = parseaddr(sender)
    sender_display = escape(display_name or sender or "No identificado")
    sender_email = escape(email_address)
    sender_line = sender_display
    if sender_email and sender_email != sender_display:
        sender_line += f"\n<code>{sender_email}</code>"

    header = (
        "📩 <b>NUEVO CORREO</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"<b>📝 Asunto</b>\n{escape(subject or 'Sin asunto')}\n\n"
        f"<b>👤 Remitente</b>\n{sender_line}\n\n"
        f"<b>🗓 Fecha</b>\n{escape(formatted_date or 'No disponible')}\n"
        "━━━━━━━━━━━━━━━━\n"
        "<b>💬 Mensaje</b>\n"
    )
    
    if html_body:
        body = clean_html(html_body)
    else:
        # Escapar explícitamente el texto plano
        body = escape(text_body)
        
    return header + (body or "<i>El correo no contiene texto.</i>")
