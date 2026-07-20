# MD Converter Telegram Bot

Send the bot any document, link, photo, or YouTube URL — it replies with the converted `.md` file plus a short preview. Thin client over the project-04 Conversion API.

## Run
```bash
uv venv .venv && uv pip install -p .venv/bin/python "python-telegram-bot>=21" httpx
# 1. Create a bot with @BotFather, copy the token
# 2. Make sure the project-04 API is running (default http://127.0.0.1:8460)
MD_BOT_TOKEN=<token> .venv/bin/python -m bot.main
```

## Configuration (env)
| Var | Default | Meaning |
|---|---|---|
| `MD_BOT_TOKEN` | — (required) | token from @BotFather |
| `MD_API_URL` | `http://127.0.0.1:8460` | project-04 Conversion API |
| `MD_API_KEY` | empty | forwarded as `X-API-Key` |
| `MD_BOT_ALLOWED_IDS` | empty = open | comma-separated Telegram user ids; `/id` tells a user theirs |

## Behavior
- Documents ≤ 20 MB (Telegram bot-API cap) → `/api/convert/file`; photos → converted as images.
- Messages containing a URL → `/api/convert/url`; YouTube links auto-detected → `/api/convert/youtube`.
- `/formats` lists live formats from the API; errors come back as polite one-liners, never stack traces.

## Tests
```bash
.venv/bin/python -m pytest tests/ -q
```
9 mocked handler tests + 1 live integration test (runs when the 04 API is up; otherwise skips).

## Status
Built + tested with mocks and live API. **Not yet run against real Telegram** — needs your `MD_BOT_TOKEN`. Docker/compose packaging pending (PLAN.md Phase 3).
