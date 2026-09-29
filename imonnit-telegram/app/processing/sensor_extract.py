from bs4 import BeautifulSoup
from typing import Dict, List

def build_summary(html: str, text: str) -> str:
    if not html:
        return text[:700] + ("..." if len(text) > 700 else "")
        
    soup = BeautifulSoup(html, 'lxml')
    pairs = []
    
    for row in soup.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        if len(cells) == 2:
            key = cells[0].get_text(strip=True).strip(":")
            val = cells[1].get_text(strip=True)
            if key and val:
                pairs.append((key, val))
                
    keywords = ["sensor", "reading", "lectura", "temperature", "temperatura", "status", "estado", "battery", "batería", "date", "fecha", "alert", "alerta"]
    filtered_pairs = []
    for k, v in pairs:
        k_lower = k.lower()
        if any(kw in k_lower for kw in keywords):
            filtered_pairs.append((k, v))
            
    if not filtered_pairs:
        for line in text.splitlines():
            parts = line.split(":", 1)
            if len(parts) == 2 and len(parts[0]) < 30:
                k_lower = parts[0].lower()
                if any(kw in k_lower for kw in keywords):
                    filtered_pairs.append((parts[0].strip(), parts[1].strip()))
                    
    if filtered_pairs:
        lines = []
        for k, v in filtered_pairs[:15]:
            k = k.replace('<', '&lt;').replace('>', '&gt;')
            v = v.replace('<', '&lt;').replace('>', '&gt;')
            lines.append(f"<b>{k}:</b> {v}")
        return "\n".join(lines)
        
    return text[:700] + ("..." if len(text) > 700 else "")
