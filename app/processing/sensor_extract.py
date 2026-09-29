from bs4 import BeautifulSoup
from typing import Dict, List

def build_summary(html: str, text: str) -> str:
    """
    Busca pares clave-valor (ej: tablas de 2 celdas o texto 'Clave: valor').
    Si no encuentra nada útil, devuelve los primeros 700 caracteres del texto.
    """
    if not html:
        return text[:700] + ("..." if len(text) > 700 else "")
        
    soup = BeautifulSoup(html, 'lxml')
    pairs = []
    
    # 1. Buscar en tablas de 2 celdas
    for row in soup.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        if len(cells) == 2:
            key = cells[0].get_text(strip=True).strip(":")
            val = cells[1].get_text(strip=True)
            if key and val:
                pairs.append((key, val))
                
    # Filtro básico (palabras clave en español/inglés relacionadas a sensores)
    keywords = ["sensor", "reading", "lectura", "temperature", "temperatura", "status", "estado", "battery", "batería", "date", "fecha", "alert", "alerta"]
    filtered_pairs = []
    for k, v in pairs:
        k_lower = k.lower()
        if any(kw in k_lower for kw in keywords):
            filtered_pairs.append((k, v))
            
    if not filtered_pairs:
        # 2. Buscar patrón "Clave: valor" en texto plano
        for line in text.splitlines():
            parts = line.split(":", 1)
            if len(parts) == 2 and len(parts[0]) < 30: # Clave corta
                k_lower = parts[0].lower()
                if any(kw in k_lower for kw in keywords):
                    filtered_pairs.append((parts[0].strip(), parts[1].strip()))
                    
    # Si encontramos pares, limitamos a 15 y devolvemos un resumen
    if filtered_pairs:
        lines = []
        for k, v in filtered_pairs[:15]:
            # Escapar para HTML de Telegram
            k = k.replace('<', '&lt;').replace('>', '&gt;')
            v = v.replace('<', '&lt;').replace('>', '&gt;')
            lines.append(f"<b>{k}:</b> {v}")
        return "\n".join(lines)
        
    # Fallback a texto
    return text[:700] + ("..." if len(text) > 700 else "")
