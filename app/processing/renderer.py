from typing import Dict, Any

def get_url_fetcher(cid_attachments: Dict[str, bytes]):
    """
    Returns a custom url_fetcher for WeasyPrint that only allows data URIs
    and cid: URIs (mapped to our attachments). Blocks HTTP/HTTPS to prevent SSRF.
    """
    def custom_fetcher(url: str, *args, **kwargs) -> dict:
        # Se importa aquí para que la API pueda arrancar en Windows sin las
        # bibliotecas nativas de WeasyPrint cuando no se solicita un PDF.
        from weasyprint import default_url_fetcher
        if url.startswith('data:'):
            return default_url_fetcher(url, *args, **kwargs)
            
        if url.startswith('cid:'):
            cid = url[4:]
            if cid in cid_attachments:
                # We need to return a dict with 'string', 'mime_type'
                return {
                    'string': cid_attachments[cid]['data'],
                    'mime_type': cid_attachments[cid]['content_type']
                }
                
        # Block anything else
        return {'string': b'', 'mime_type': 'text/plain'}
        
    return custom_fetcher

def render_to_pdf(html_content: str, cid_attachments: Dict[str, Dict[str, Any]]) -> bytes:
    """Renders HTML to PDF blocking external resources and resolving CIDs."""
    from weasyprint import HTML
    fetcher = get_url_fetcher(cid_attachments)
    return HTML(string=html_content, url_fetcher=fetcher).write_pdf()
