"""Telegram handlers: documents, photos, URLs, commands."""

import io
import re

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from .api_client import ApiClient, ApiError
from .config import Config

URL_RE = re.compile(r"https?://\S+")
YOUTUBE_RE = re.compile(
    r"https?://(www\.|m\.)?(youtube\.com/(watch\?|shorts/)|youtu\.be/)\S+", re.IGNORECASE
)
TELEGRAM_DOWNLOAD_LIMIT = 20 * 1024 * 1024  # bot API cap

PREVIEW_CHARS = 900


def _filename_for(title: str | None, fallback: str = "converted") -> str:
    base = re.sub(r"[^\w\d-]+", "-", title or fallback).strip("-")[:80]
    return (base or fallback) + ".md"


def _preview(markdown: str) -> str:
    body = markdown
    if body.startswith("---"):
        end = body.find("---", 3)
        if end != -1:
            body = body[end + 3 :].strip()
    if len(body) > PREVIEW_CHARS:
        body = body[:PREVIEW_CHARS] + "…"
    return body


async def _reply_result(update: Update, body: dict, fallback_name: str) -> None:
    markdown = body["markdown"]
    filename = _filename_for(body.get("title"), fallback_name)
    doc = io.BytesIO(markdown.encode("utf-8"))
    doc.name = filename
    caption = (body.get("title") or filename)[:1000]
    await update.effective_message.reply_document(document=doc, caption=caption)
    await update.effective_message.reply_text(_preview(markdown))


def _gate(cfg: Config):
    async def check(update: Update) -> bool:
        user = update.effective_user
        if not cfg.allowed(user.id if user else None):
            await update.effective_message.reply_text(
                "Sorry, this bot is private. Ask the owner to add your id "
                f"({user.id if user else '?'}) to MD_BOT_ALLOWED_IDS."
            )
            return False
        return True

    return check


def build_handlers(cfg: Config, api: ApiClient):
    allowed = _gate(cfg)

    async def start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_message.reply_text(
            "Markdrop bot — from Dhiva Labs.\nSend me any document (pdf, docx, xlsx, pptx, epub, csv, …), a link, "
            "or a YouTube URL and I'll reply with a Markdown file.\n"
            "Commands: /formats — supported formats, /id — your Telegram id."
        )

    async def user_id(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_message.reply_text(str(update.effective_user.id))

    async def formats(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await allowed(update):
            return
        try:
            body = await api.formats()
            live = [k for k, v in body.get("extras", {}).items() if v]
            await update.effective_message.reply_text(
                "Always: " + ", ".join(body.get("always", [])) + "\nExtras: " + ", ".join(live)
            )
        except Exception as e:
            await update.effective_message.reply_text(f"Could not reach the converter: {e}")

    async def on_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await allowed(update):
            return
        msg = update.effective_message
        doc = msg.document
        if doc.file_size and doc.file_size > TELEGRAM_DOWNLOAD_LIMIT:
            await msg.reply_text("That file is over Telegram's 20 MB bot limit — use the web converter for big files.")
            return
        await msg.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        try:
            tg_file = await ctx.bot.get_file(doc.file_id)
            data = bytes(await tg_file.download_as_bytearray())
            body = await api.convert_file(doc.file_name or "upload", data)
            await _reply_result(update, body, (doc.file_name or "upload").rsplit(".", 1)[0])
        except ApiError as e:
            await msg.reply_text(f"Conversion failed: {e}")
        except Exception:
            await msg.reply_text("Something went wrong handling that file.")

    async def on_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await allowed(update):
            return
        msg = update.effective_message
        await msg.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        try:
            photo = msg.photo[-1]  # largest size
            tg_file = await ctx.bot.get_file(photo.file_id)
            data = bytes(await tg_file.download_as_bytearray())
            body = await api.convert_file("photo.jpg", data)
            await _reply_result(update, body, "photo")
        except ApiError as e:
            await msg.reply_text(f"Conversion failed: {e}")

    async def on_text(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await allowed(update):
            return
        msg = update.effective_message
        text = msg.text or ""
        m = URL_RE.search(text)
        if not m:
            await msg.reply_text("Send a file, a link, or a YouTube URL.")
            return
        url = m.group(0)
        await msg.chat.send_action(ChatAction.TYPING)
        try:
            if YOUTUBE_RE.match(url):
                body = await api.convert_youtube(url)
            else:
                body = await api.convert_url(url)
            await _reply_result(update, body, "page")
        except ApiError as e:
            await msg.reply_text(f"Conversion failed: {e}")

    return {
        "start": start,
        "id": user_id,
        "formats": formats,
        "document": on_document,
        "photo": on_photo,
        "text": on_text,
    }
