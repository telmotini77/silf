from datetime import datetime, timezone

import pytest
from sqlalchemy.dialects import postgresql

from app.models import Message, MessageStatus, RawType
from app.telegram.client import TelegramPermanentError
from app.worker import dispatcher, scheduler


class FakeResult:
    def __init__(self, rowcount=0):
        self.rowcount = rowcount


class FakeSession:
    def __init__(self, message=None):
        self.message = message
        self.statements = []
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, model, message_id):
        return self.message

    async def execute(self, statement):
        self.statements.append(statement)
        return FakeResult()

    async def commit(self):
        self.commits += 1


def sending_message(attempts=1):
    return Message(
        id=1, raw=b"", raw_type=RawType.EML, status=MessageStatus.SENDING,
        attempts=attempts, delivery={},
    )


@pytest.fixture
def run_process(monkeypatch):
    async def run(message, outcome):
        session = FakeSession(message)
        monkeypatch.setattr(dispatcher, "AsyncSessionLocal", lambda: session)

        async def fake_deliver(db, msg):
            if outcome is not None:
                raise outcome

        monkeypatch.setattr(dispatcher, "deliver_message", fake_deliver)
        await dispatcher.process_message(message.id)
        return session

    return run


@pytest.mark.asyncio
async def test_successful_delivery_marks_sent(run_process):
    message = sending_message()
    session = await run_process(message, None)

    assert message.status == MessageStatus.SENT
    assert message.sent_at is not None
    assert session.commits == 1


@pytest.mark.asyncio
async def test_permanent_error_marks_failed(run_process):
    message = sending_message()
    await run_process(message, TelegramPermanentError("HTTP 403: Forbidden"))

    assert message.status == MessageStatus.FAILED
    assert "403" in message.last_error


@pytest.mark.asyncio
async def test_transient_error_schedules_retry_with_backoff(run_process):
    message = sending_message(attempts=2)
    before = datetime.now(timezone.utc)
    await run_process(message, RuntimeError("network down"))

    assert message.status == MessageStatus.RETRY
    delay = (message.next_attempt_at - before).total_seconds()
    assert 59 <= delay <= 61  # 30 * 2 ** (2 - 1)


@pytest.mark.asyncio
async def test_transient_error_on_last_attempt_marks_failed(run_process):
    message = sending_message(attempts=dispatcher.MAX_ATTEMPTS)
    await run_process(message, RuntimeError("network down"))

    assert message.status == MessageStatus.FAILED
    assert message.next_attempt_at is None


@pytest.mark.asyncio
async def test_message_no_longer_sending_is_skipped(run_process):
    message = sending_message()
    message.status = MessageStatus.SENT
    session = await run_process(message, RuntimeError("should not run"))

    assert message.status == MessageStatus.SENT
    assert session.commits == 0


@pytest.mark.asyncio
async def test_recovery_fails_exhausted_messages_instead_of_requeueing(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(scheduler, "AsyncSessionLocal", lambda: session)

    await scheduler.recover_stuck_messages()

    fail_sql, retry_sql = (
        str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        for statement in session.statements
    )
    assert f"attempts >= {dispatcher.MAX_ATTEMPTS}" in fail_sql
    assert "'FAILED'" in fail_sql and "'RETRY'" in fail_sql
    assert f"attempts < {dispatcher.MAX_ATTEMPTS}" in retry_sql
    assert "status='RETRY'" in retry_sql.replace(" ", "")
    assert session.commits == 1
