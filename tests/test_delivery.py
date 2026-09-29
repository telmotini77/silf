import pytest

from app.models import Message, RawType
from app.worker import delivery


class FakeSession:
    def __init__(self):
        self.snapshots = []

    async def commit(self):
        self.snapshots.append(dict(self.message.delivery))


class FlakyTelegram:
    """Confirma la primera parte y falla en la segunda."""

    def __init__(self, fail_on_call=None):
        self.calls = []
        self.fail_on_call = fail_on_call

    async def send_message(self, text, reply_to=None):
        self.calls.append(reply_to)
        if len(self.calls) == self.fail_on_call:
            raise RuntimeError("network down")
        return str(100 + len(self.calls))


@pytest.fixture
def long_message(sample_email_bytes, monkeypatch):
    monkeypatch.setattr(delivery, "split_message", lambda text: ["parte 0", "parte 1", "parte 2"])
    return Message(raw=sample_email_bytes, raw_type=RawType.EML, delivery={})


@pytest.mark.asyncio
async def test_partial_delivery_is_persisted_and_resumed(long_message, monkeypatch):
    db = FakeSession()
    db.message = long_message

    first = FlakyTelegram(fail_on_call=2)
    monkeypatch.setattr(delivery, "telegram_client", first)
    with pytest.raises(RuntimeError):
        await delivery.deliver_message(db, long_message)

    assert long_message.delivery == {"text:0": "101"}
    assert db.snapshots == [{"text:0": "101"}]

    retry = FlakyTelegram()
    monkeypatch.setattr(delivery, "telegram_client", retry)
    await delivery.deliver_message(db, long_message)

    # Solo se envían las partes pendientes, respondiendo al primer mensaje.
    assert retry.calls == ["101", "101"]
    assert long_message.delivery == {"text:0": "101", "text:1": "101", "text:2": "102"}
