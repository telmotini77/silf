from app.processing.parser import parse_mime

def test_parser(sample_email_bytes):
    parsed = parse_mime(sample_email_bytes)
    assert parsed.subject == 'Alerta iMonnit'
    assert 'alertas@imonnit.com' in parsed.sender
    assert len(parsed.attachments) == 2
    
    inline_att = next(a for a in parsed.attachments if a['inline'])
    assert inline_att['content_id'] == 'imagen_logo'
    
    normal_att = next(a for a in parsed.attachments if not a['inline'])
    assert normal_att['filename'] == 'data.csv'
