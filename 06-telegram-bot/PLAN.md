# Project 6 — MD Converter Telegram Bot

Send the bot any file, link, or YouTube URL from any device; it replies with the converted `.md` document. Zero-install mobile access to the suite.

## Stack
- **Python + python-telegram-bot v21+** (async, long-polling by default — no public IP/webhook needed; webhook mode optional for deployment).
- Conversion via the **project-04 Conversion API** (`MD_API_URL`, default `http://127.0.0.1:8460`) so the bot stays a thin client — no heavy deps, no duplicate engine. Falls back with a clear error if the API is down.
- Single small container / systemd service; runs alongside the 04 stack (docker-compose entry).

## Features

### MVP (Phase 1)
1. **Send a document** (pdf/docx/xlsx/pptx/epub/csv/…, ≤ 20 MB Telegram bot-API download limit) → bot downloads, posts to API `/convert/file`, replies with a `.md` document + title caption.
2. **Send a URL** (plain message containing a link) → `/convert/url`; YouTube links auto-detected → `/convert/youtube`.
3. **Send a photo** → converted via API (image metadata; OCR later when the API grows it).
4. `/start` + `/help` with format list pulled live from `/api/formats`.
5. Errors surfaced politely (unsupported type, too large, API down), never stack traces.

### Phase 2
6. **Access control**: `MD_BOT_ALLOWED_IDS` (comma-separated Telegram user ids) — closed by default so a public token leak can't turn it into an open converter; `/id` command tells a user their id.
7. **Inline preview**: reply includes the first ~1500 chars as a quoted message plus the file.
8. **Batch**: media-group albums of documents → one zip of .md files.
9. **/timestamps toggle** for YouTube transcripts (uses connector-style stamped output once API exposes it).

### Phase 3 (deploy)
10. Dockerfile + docker-compose service next to 04; webhook mode behind the same reverse proxy; health logging.

## Architecture
```
bot/
  main.py          # Application builder, handlers registration
  handlers.py      # document / url / photo / commands
  api_client.py    # thin async client for the 04 API (httpx)
  config.py        # env: MD_BOT_TOKEN, MD_API_URL, MD_API_KEY, MD_BOT_ALLOWED_IDS
tests/             # handler tests with mocked API + mocked bot context
Dockerfile
```

## Verification
- pytest with a mocked API client and python-telegram-bot's test utilities (no live Telegram needed).
- Live smoke test needs a bot token from @BotFather (user provides `MD_BOT_TOKEN`); then: send test.docx, a Wikipedia URL, a YouTube link from the phone and check replies.

## Risks
- Telegram bot-API file download cap: 20 MB (50 MB for uploads) — clear error message; big files remain a job for the web UI.
- Long conversions vs. Telegram's expectations — send "typing…"/progress action, API timeout already capped at 60 s.
- Token secrecy: token only via env; allowlist on by default once configured.
