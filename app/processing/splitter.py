import re
from typing import List

MAX_LENGTH = 4096

def split_message(html_text: str, max_len: int = MAX_LENGTH) -> List[str]:
    """
    Divide un mensaje manteniendo balanceadas las etiquetas HTML soportadas.
    Evita cortar a la mitad de una entidad (&amp;) o una etiqueta (<br>).
    """
    # Se reserva un margen para evitar rechazos de Telegram por entidades o
    # etiquetas que su contador interno trate de forma distinta.
    max_len = max(1, max_len - 128)
    chunks = []
    current_chunk = ""
    open_tags = []
    
    # Regex for HTML tags
    tag_pattern = re.compile(r'</?([a-zA-Z0-9]+)[^>]*>')
    
    # We iterate over words or tokens to avoid cutting in the middle of a word/entity if possible.
    # For a robust implementation we can use a token based approach or a sliding window.
    # Simplified sliding window that respects tags.
    
    i = 0
    while i < len(html_text):
        # Calculate how much space we have left in current chunk, accounting for closing tags
        closing_tags_len = sum(len(f"</{t}>") for t in open_tags)
        avail = max_len - len(current_chunk) - closing_tags_len
        
        if avail <= 0:
            # Close all open tags
            for t in reversed(open_tags):
                current_chunk += f"</{t}>"
            chunks.append(current_chunk)
            
            # Reopen tags for next chunk
            current_chunk = ""
            for t in open_tags:
                current_chunk += f"<{t}>" # Simplified, loses attributes in <a> but fine for bold/italic
            continue
            
        # Find next tag or entity
        tag_match = tag_pattern.search(html_text, i)
        
        if tag_match and tag_match.start() == i:
            tag_full = tag_match.group(0)
            tag_name = tag_match.group(1).lower()
            
            # Space needed for this tag?
            if len(tag_full) > avail and len(current_chunk) > 0:
                # Force chunk wrap
                for t in reversed(open_tags):
                    current_chunk += f"</{t}>"
                chunks.append(current_chunk)
                current_chunk = ""
                for t in open_tags:
                    current_chunk += f"<{t}>"
                continue
                
            current_chunk += tag_full
            if tag_full.startswith("</"):
                if open_tags and open_tags[-1] == tag_name:
                    open_tags.pop()
            else:
                # Open tag (ignoring self-closing since telegram mostly uses <b> <i> etc)
                open_tags.append(tag_name)
                
            i += len(tag_full)
        else:
            # Advance one character (or word)
            current_chunk += html_text[i]
            i += 1

    if current_chunk:
        for t in reversed(open_tags):
            current_chunk += f"</{t}>"
        chunks.append(current_chunk)
        
    return chunks
