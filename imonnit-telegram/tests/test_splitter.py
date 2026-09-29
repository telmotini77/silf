from app.processing.splitter import split_message

def test_splitter():
    html = "<b>Texto largo " + "a" * 4000 + " final</b>"
    chunks = split_message(html, 4096)
    
    assert len(chunks) > 1
    assert chunks[0].endswith("</b>")
    assert chunks[1].startswith("<b>")
    assert "final" in chunks[-1]
