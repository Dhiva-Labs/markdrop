# md-files-dhivalabs — Master Plan

One suite, five products (sixth TBD), all built around "convert anything → Markdown", powered by the MarkItDown engine (analysis in `notes/markitdown-analysis.md`, source in `reference/markitdown/`).

## Projects

| # | Folder | Product | Stack | Plan |
|---|--------|---------|-------|------|
| 1 | `01-browser-extension/` | MD Clipper — browser extension | TypeScript, Manifest V3 (Chrome + Firefox) | [PLAN](01-browser-extension/PLAN.md) |
| 2 | `02-mobile-app/` | MD Converter mobile app | Flutter (Android-first) + Chaquopy Python engine | [PLAN](02-mobile-app/PLAN.md) |
| 3 | `03-desktop-app/` | MD Converter desktop (Linux/Win/Mac) | Flutter desktop + PyInstaller markitdown sidecar | [PLAN](03-desktop-app/PLAN.md) |
| 4 | `04-web-app/` | Web converter + shared conversion API | FastAPI (markitdown[all]) + static frontend, Docker | [PLAN](04-web-app/PLAN.md) |
| 5 | `05-claude-connector/` | Claude connector (MCP server + skill) | Python MCP (stdio + HTTP) | [PLAN](05-claude-connector/PLAN.md) |
| 6 | `06-telegram-bot/` | MD Converter Telegram bot | Python, python-telegram-bot, thin client over 04's API | [PLAN](06-telegram-bot/PLAN.md) |

## Shared architecture

```
                 ┌─────────────────────────────┐
                 │  markitdown engine (Python) │  ← reference/markitdown
                 └──────┬──────────┬───────────┘
        embedded via    │          │ wrapped by
   ┌────────────────────┤          ├─────────────────────┐
   │ PyInstaller sidecar│          │ FastAPI service      │
   │ (03 desktop)       │          │ (04 web-app backend) │
   │ Chaquopy (02 mobile)│         │  ▲          ▲        │
   └────────────────────┘          └──┼──────────┼────────┘
                                      │          │ optional "power mode" API
                          01 extension│          │ 02 mobile fallback
                                      │
                 05 connector = MCP server wrapping engine directly
```

- **The engine is always MarkItDown** — we never re-implement converters in another language, except in the browser extension where page→md must run client-side (Readability + Turndown there, same output conventions).
- **04's FastAPI service doubles as the shared Conversion API** used by the extension (for PDFs/office files/YouTube) and optionally by mobile. Build it early.
- Common markdown output conventions across all apps: ATX headings, pipe tables, front-matter block (`source`, `title`, `date`, `type`) — defined once in `04-web-app/PLAN.md` §Output-spec and reused everywhere.

## Recommended build order

1. **04 web-app** (backend first — it's the shared API; frontend after)
2. **05 claude-connector** (small; reuses engine directly; immediately useful to us)
3. **01 browser-extension** (client-side core + calls API for heavy formats)
4. **03 desktop-app** (Flutter desktop is your proven stack; sidecar pattern)
5. **02 mobile-app** (hardest: Python-on-Android; benefits from all prior work)

## Open questions for verification
1. What is project **#6**? (message was cut off)
2. Mobile: sentence cut off at "this should be …" — assumed **Flutter, Android-first** (matching your other projects). Confirm.
3. Web app hosting target? Plan assumes **self-hosted Docker** (works on your machine / any VPS); no paid cloud assumed.
4. Each project gets its own git repo, or one mono-repo at `md-files-dhivalabs`? Plan assumes **one repo, folders as workspaces** until you say otherwise.
5. LLM-dependent features (image captioning, LLM OCR) are planned as **optional/off by default** (need an API key). OK?
