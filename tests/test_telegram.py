import httpx
import pytest

from app.telegram import client as telegram_module
from app.telegram.client import TelegramClient, TelegramError, TelegramPermanentError


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def fake_sleep(_):
        return None

    monkeypatch.setattr(telegram_module.asyncio, "sleep", fake_sleep)


def make_client(handler):
    client = TelegramClient()
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


def ok(message_id=42):
    return httpx.Response(200, json={"ok": True, "result": {"message_id": message_id}})


@pytest.mark.asyncio
async def test_persistent_rate_limit_raises_instead_of_returning_none():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, json={"description": "Too Many Requests", "parameters": {"retry_after": 1}})

    with pytest.raises(TelegramError, match="429"):
        await make_client(handler).send_message("hola")
    assert len(calls) == 5


@pytest.mark.asyncio
async def test_non_json_server_error_is_transient():
    def handler(request):
        return httpx.Response(502, text="<html>Bad Gateway</html>")

    with pytest.raises(TelegramError) as error:
        await make_client(handler).send_message("hola")
    assert not isinstance(error.value, TelegramPermanentError)


@pytest.mark.asyncio
async def test_rate_limit_then_success_returns_message_id():
    responses = iter([httpx.Response(429, json={"parameters": {"retry_after": 1}}), ok(7)])

    assert await make_client(lambda request: next(responses)).send_message("hola") == "7"


@pytest.mark.asyncio
async def test_parse_error_falls_back_to_plain_text():
    modes = []

    def handler(request):
        body = request.content.decode()
        modes.append("parse_mode=HTML" in body)
        if "parse_mode=HTML" in body:
            return httpx.Response(400, json={"description": "Bad Request: can't parse entities"})
        return ok(9)

    assert await make_client(handler).send_message("<b>roto") == "9"
    assert modes == [True, False]


@pytest.mark.asyncio
async def test_forbidden_is_permanent():
    def handler(request):
        return httpx.Response(403, json={"description": "Forbidden: bot was kicked"})

    with pytest.raises(TelegramPermanentError):
        await make_client(handler).send_message("hola")
