import pytest
from app.processing.parser import parse_mime
from app.processing.formatter import build_equivalent, clean_html
from app.processing.sensor_extract import build_summary
from app.processing.splitter import split_message

def test_parser(sample_email_bytes):
    parsed = parse_mime(sample_email_bytes)
    assert parsed.subject == 'Alerta de Carbonio'
    assert 'alertas@futurity.com.ec' in parsed.sender
    assert len(parsed.attachments) == 2
    
    # Check inline detection
    inline_att = next(a for a in parsed.attachments if a['inline'])
    assert inline_att['content_id'] == 'imagen_logo'
    assert inline_att['content_type'] == 'image/png'
    
    normal_att = next(a for a in parsed.attachments if not a['inline'])
    assert normal_att['filename'] == 'data.csv'

def test_formatter_clean_html(sample_email_bytes):
    parsed = parse_mime(sample_email_bytes)
    cleaned = clean_html(parsed.html)
    
    # Sanitization
    assert '<script>' not in cleaned
    assert 'Preheader secreto' not in cleaned # Hidden text removed
    assert '<style>' not in cleaned
    
    # Structure conversion
    assert '<b>Alerta Crítica</b>' in cleaned # h1 -> b
    assert '<b>Sensor:</b> Temperatura Sala 1' in cleaned # Table 2 cells
    assert '• Acción requerida' in cleaned # li -> bullet
    
    # Links
    assert 'href="https://example.com"' in cleaned
    assert 'href="javascript:alert(1)"' not in cleaned
    assert 'Enlace Malo' in cleaned # Text is preserved

def test_formatter_build_equivalent(sample_email_bytes, monkeypatch):
    import app.config
    monkeypatch.setattr(app.config.settings, "TIMEZONE", "America/Guayaquil")
    
    parsed = parse_mime(sample_email_bytes)
    eq = build_equivalent(parsed.subject, parsed.sender, parsed.date, parsed.html, parsed.text)
    
    # Timezone conversion (10:00 UTC -> 05:00 ECT)
    assert '05:00:00' in eq
    assert '📩 <b>NUEVO CORREO</b>' in eq
    assert '<b>📝 Asunto</b>\nAlerta de Carbonio' in eq
    assert '<b>👤 Remitente</b>' in eq
    assert 'alertas@futurity.com.ec' in eq
    assert '<b>💬 Mensaje</b>' in eq

def test_sensor_extract(sample_email_bytes):
    parsed = parse_mime(sample_email_bytes)
    summary = build_summary(parsed.html, parsed.text)
    assert '<b>Sensor:</b> Temperatura Sala 1' in summary
    assert '<b>Estado:</b> Fuera de rango' in summary

def test_splitter():
    html = "<b>Texto largo " + "a" * 4000 + " final</b>"
    chunks = split_message(html, 4096)
    
    assert len(chunks) > 1
    # Check that tags are balanced
    assert chunks[0].endswith("</b>")
    assert chunks[1].startswith("<b>")
    
    assert "final" in chunks[-1]
