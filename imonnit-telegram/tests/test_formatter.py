from app.processing.formatter import clean_html, build_equivalent
from app.processing.parser import parse_mime
import app.config

def test_formatter_clean_html(sample_email_bytes, monkeypatch):
    monkeypatch.setattr(app.config.settings, "TIMEZONE", "America/Guayaquil")
    parsed = parse_mime(sample_email_bytes)
    cleaned = clean_html(parsed.html)
    
    assert '<script>' not in cleaned
    assert 'Preheader secreto' not in cleaned
    assert '<style>' not in cleaned
    assert '<b>Alerta Crítica</b>' in cleaned
    assert '<b>Sensor:</b> Temperatura Sala 1' in cleaned
    assert '• Acción requerida' in cleaned
    assert 'javascript:' not in cleaned

def test_build_equivalent(sample_email_bytes, monkeypatch):
    monkeypatch.setattr(app.config.settings, "TIMEZONE", "America/Guayaquil")
    parsed = parse_mime(sample_email_bytes)
    eq = build_equivalent(parsed.subject, parsed.sender, parsed.date, parsed.html, parsed.text)
    assert '05:00:00' in eq
    assert '🔔 <b>Asunto:</b> Alerta iMonnit' in eq
