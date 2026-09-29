import pytest
from unittest.mock import AsyncMock, MagicMock
from app.imap.receiver import handle_new_uids, sync_mailbox
from app.models import MailboxState
import app.config

@pytest.mark.asyncio
async def test_handle_new_uids(monkeypatch):
    mock_fetch = AsyncMock(return_value=b"Subject: Test\nFrom: test@test.com\n\n")
    monkeypatch.setattr("app.imap.receiver.fetch_headers", mock_fetch)
    mock_ingest = AsyncMock()
    monkeypatch.setattr("app.imap.receiver.ingest_email", mock_ingest)
    
    client = AsyncMock()
    await handle_new_uids(client, [10, 11], "INBOX", 12345)
    
    assert mock_fetch.call_count == 2
    assert mock_ingest.call_count == 2
