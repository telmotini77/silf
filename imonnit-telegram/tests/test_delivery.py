import pytest
from unittest.mock import AsyncMock, patch
from app.worker.delivery import deliver_message
from app.models import Message

@pytest.mark.asyncio
async def test_delivery_idempotent(sample_email_bytes, monkeypatch):
    import app.config
    monkeypatch.setattr(app.config.settings, "TELEGRAM_MODE", "equivalent")
    
    mock_send = AsyncMock(return_value="100")
    monkeypatch.setattr("app.telegram.client.TelegramClient.send_message", mock_send)
    
    msg = Message(id=1, folder="INBOX", uid=10, uidvalidity=123, raw=sample_email_bytes, delivery={})
    db = AsyncMock()
    
    await deliver_message(db, msg)
    assert mock_send.call_count == 1
    assert msg.delivery.get("equivalent:0") == "100"
    
    # Second time, should not send again
    await deliver_message(db, msg)
    assert mock_send.call_count == 1 # Still 1
