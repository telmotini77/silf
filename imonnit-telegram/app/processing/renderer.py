from weasyprint import HTML, default_url_fetcher
from typing import Dict, Any

def get_url_fetcher(cid_attachments: Dict[str, bytes]):
    def custom_fetcher(url: str, *args, **kwargs) -> dict:
        if url.startswith('data:'):
            return default_url_fetcher(url, *args, **kwargs)
            
        if url.startswith('cid:'):
            cid = url[4:]
            if cid in cid_attachments:
                return {
                    'string': cid_attachments[cid]['data'],
                    'mime_type': cid_attachments[cid]['content_type']
                }
                
        return {'string': b'', 'mime_type': 'text/plain'}
        
    return custom_fetcher

def render_to_pdf(html_content: str, cid_attachments: Dict[str, Dict[str, Any]]) -> bytes:
    fetcher = get_url_fetcher(cid_attachments)
    return HTML(string=html_content, url_fetcher=fetcher).write_pdf()
