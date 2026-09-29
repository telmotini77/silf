import nh3
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from app.config import settings
import re

def clean_html(html_str: str) -> str:
    soup = BeautifulSoup(html_str, 'lxml')
    for tag in soup(["script", "style", "head", "title", "meta", "svg", "form"]):
        tag.decompose()
        
    for tag in soup.find_all(lambda t: t.has_attr('hidden') or 
                             ('display' in t.get('style', '') and 'none' in t.get('style', '')) or 
                             ('visibility' in t.get('style', '') and 'hidden' in t.get('style', ''))):
        tag.decompose()
        
    for i in range(1, 7):
        for tag in soup.find_all(f'h{i}'):
            tag.name = 'b'
            
    for li in soup.find_all('li'):
        li.insert_before("• ")
        li.unwrap()
        
    for br in soup.find_all('br'):
        br.replace_with("\n")
    for hr in soup.find_all('hr'):
        hr.replace_with("\n---\n")

    for table in soup.find_all('table'):
        table_text = []
        for row in table.find_all('tr', recursive=False):
            cells = row.find_all(['td', 'th'], recursive=False)
            if len(cells) == 2 and len(cells[0].get_text(strip=True)) < 30:
                table_text.append(f"<b>{cells[0].get_text(strip=True)}:</b> {cells[1].get_text(strip=True)}")
            elif len(cells) == 1:
                table_text.append(cells[0].get_text(strip=True))
            elif len(cells) > 2:
                table_text.append(" | ".join(c.get_text(strip=True) for c in cells))
        table.replace_with("\n".join(table_text) + "\n")

    for img in soup.find_all('img'):
        img.decompose()
        
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if not href.startswith(('http://', 'https://', 'mailto:')):
            a.unwrap()

    raw_text = str(soup)
    
    ALLOWED_TAGS = {'b', 'strong', 'i', 'em', 'u', 's', 'del', 'strike', 'a', 'code', 'pre', 'blockquote'}
    ALLOWED_ATTRS = {'a': {'href'}, 'code': {'class'}}
    
    final_html = nh3.clean(raw_text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
    final_html = re.sub(r'\n{3,}', '\n\n', final_html)
    
    return final_html.strip()

def build_equivalent(subject: str, sender: str, date_str: str, html_body: str, text_body: str) -> str:
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        local_tz = pytz.timezone(settings.TIMEZONE)
        local_dt = dt.astimezone(local_tz)
        formatted_date = local_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        formatted_date = date_str

    header = (
        f"🔔 <b>Asunto:</b> {subject}\n"
        f"<b>De:</b> {sender}\n"
        f"<b>Fecha:</b> {formatted_date}\n"
        f"──────────────\n"
    )
    
    if html_body:
        body = clean_html(html_body)
    else:
        body = text_body.replace('<', '&lt;').replace('>', '&gt;')
        
    return header + body
