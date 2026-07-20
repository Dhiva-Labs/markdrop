"""Handler tests with mocked Telegram objects and a mocked/real API client."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.api_client import ApiClient, ApiError  # noqa: E402
from bot.config import Config  # noqa: E402
from bot.handlers import URL_RE, YOUTUBE_RE, _filename_for, _preview, build_handlers  # noqa: E402


def make_update(text=None, user_id=42, document=None, photo=None):
    msg = MagicMock()
    msg.text = text
    msg.document = document
    msg.photo = photo
    msg.reply_text = AsyncMock()
    msg.reply_document = AsyncMock()
    msg.chat.send_action = AsyncMock()
    update = MagicMock()
    update.effective_message = msg
    update.effective_user = SimpleNamespace(id=user_id)
    return update


def make_ctx():
    ctx = MagicMock()
    ctx.bot.get_file = AsyncMock()
    return ctx


@pytest.fixture
def api():
    client = MagicMock(spec=ApiClient)
    client.convert_url = AsyncMock(return_value={"ok": True, "title": "Page", "markdown": "---\nx\n---\n\nbody"})
    client.convert_youtube = AsyncMock(return_value={"ok": True, "title": "Vid", "markdown": "---\nx\n---\n\ntranscript"})
    client.convert_file = AsyncMock(return_value={"ok": True, "title": "Doc", "markdown": "---\nx\n---\n\ncontent"})
    return client


@pytest.fixture
def handlers(api):
    return build_handlers(Config(), api)


def test_regexes():
    assert YOUTUBE_RE.match("https://www.youtube.com/watch?v=jNQXAC9IVRw")
    assert YOUTUBE_RE.match("https://youtu.be/jNQXAC9IVRw")
    assert not YOUTUBE_RE.match("https://example.com/watch?v=x")
    assert URL_RE.search("see https://a.dev/x ok").group(0) == "https://a.dev/x"


def test_filename_and_preview():
    assert _filename_for("Hello, World!") == "Hello-World.md"
    assert _filename_for(None) == "converted.md"
    assert _preview("---\ntitle: t\n---\n\nreal body") == "real body"


@pytest.mark.asyncio
async def test_text_url_routes_to_convert_url(handlers, api):
    upd = make_update(text="convert https://example.com/a please")
    await handlers["text"](upd, make_ctx())
    api.convert_url.assert_awaited_once_with("https://example.com/a")
    upd.effective_message.reply_document.assert_awaited_once()


@pytest.mark.asyncio
async def test_text_youtube_routes_to_convert_youtube(handlers, api):
    upd = make_update(text="https://youtu.be/jNQXAC9IVRw")
    await handlers["text"](upd, make_ctx())
    api.convert_youtube.assert_awaited_once()
    api.convert_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_text_without_url_prompts(handlers, api):
    upd = make_update(text="hello")
    await handlers["text"](upd, make_ctx())
    api.convert_url.assert_not_awaited()
    upd.effective_message.reply_text.assert_awaited()


@pytest.mark.asyncio
async def test_document_flow(handlers, api):
    doc = SimpleNamespace(file_id="f1", file_name="report.pdf", file_size=1000)
    upd = make_update(document=doc)
    ctx = make_ctx()
    tg_file = MagicMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"%PDF"))
    ctx.bot.get_file.return_value = tg_file
    await handlers["document"](upd, ctx)
    api.convert_file.assert_awaited_once_with("report.pdf", b"%PDF")
    upd.effective_message.reply_document.assert_awaited_once()


@pytest.mark.asyncio
async def test_document_too_big_rejected(handlers, api):
    doc = SimpleNamespace(file_id="f1", file_name="big.pdf", file_size=25 * 1024 * 1024)
    upd = make_update(document=doc)
    await handlers["document"](upd, make_ctx())
    api.convert_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_api_error_reported_politely(handlers, api):
    api.convert_url.side_effect = ApiError("Unsupported file type")
    upd = make_update(text="https://example.com/x.bin")
    await handlers["text"](upd, make_ctx())
    reply = upd.effective_message.reply_text.await_args.args[0]
    assert "Unsupported file type" in reply


@pytest.mark.asyncio
async def test_allowlist_blocks_strangers(api, monkeypatch):
    monkeypatch.setenv("MD_BOT_ALLOWED_IDS", "1,2")
    handlers = build_handlers(Config(), api)
    upd = make_update(text="https://example.com", user_id=999)
    await handlers["text"](upd, make_ctx())
    api.convert_url.assert_not_awaited()
    assert "private" in upd.effective_message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_live_api_roundtrip_if_running():
    """Integration: uses the real project-04 API when it's up; skipped otherwise."""
    import httpx

    client = ApiClient("http://127.0.0.1:8460")
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get("http://127.0.0.1:8460/api/health")
            assert r.status_code == 200
    except Exception:
        pytest.skip("project-04 API not running")
    body = await client.convert_url("https://en.wikipedia.org/wiki/Markdown")
    assert body["ok"] and "Markdown" in body["markdown"]
