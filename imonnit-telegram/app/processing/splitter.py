import re
from typing import List

MAX_LENGTH = 4096

def split_message(html_text: str, max_len: int = MAX_LENGTH) -> List[str]:
    chunks = []
    current_chunk = ""
    open_tags = []
    tag_pattern = re.compile(r'</?([a-zA-Z0-9]+)[^>]*>')
    
    i = 0
    while i < len(html_text):
        closing_tags_len = sum(len(f"</{t}>") for t in open_tags)
        avail = max_len - len(current_chunk) - closing_tags_len
        
        if avail <= 0:
            for t in reversed(open_tags):
                current_chunk += f"</{t}>"
            chunks.append(current_chunk)
            
            current_chunk = ""
            for t in open_tags:
                current_chunk += f"<{t}>"
            continue
            
        tag_match = tag_pattern.search(html_text, i)
        
        if tag_match and tag_match.start() == i:
            tag_full = tag_match.group(0)
            tag_name = tag_match.group(1).lower()
            
            if len(tag_full) > avail and len(current_chunk) > 0:
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
                open_tags.append(tag_name)
                
            i += len(tag_full)
        else:
            current_chunk += html_text[i]
            i += 1

    if current_chunk:
        for t in reversed(open_tags):
            current_chunk += f"</{t}>"
        chunks.append(current_chunk)
        
    return chunks
