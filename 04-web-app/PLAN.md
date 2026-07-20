# Project 4 — MD Converter Web (Site + Shared Conversion API)

Public-facing web page where anyone can upload a file / paste a URL / paste a YouTube link and get Markdown. Its backend doubles as the **shared Conversion API** used by the browser extension (heavy formats) and optionally the mobile app ("power mode").

## Stack
- **Backend: FastAPI** (Python) wrapping `markitdown[all]` + youtube-transcript-api. Uvicorn, Docker image (extend upstream's Dockerfile pattern).
- **Frontend: static SPA** — plain TypeScript + Vite (no heavy framework), served by the same FastAPI app. Markdown preview via `marked` + sanitize, highlight for code blocks.
- Single container deploy; runs on this machine or any VPS. No DB — stateless, files processed in-memory/tmp and deleted.

## API design (v1)
```
POST /api/convert/file      multipart upload (+ optional hints: extension, mimetype, charset)
POST /api/convert/url       {"url": "..."}          # pages, direct file links, wikipedia/rss
POST /api/convert/youtube   {"url": "..."}          # metadata + transcript md
GET  /api/formats           # supported formats + which extras are live
GET  /api/health
→ all return {"ok", "title", "markdown", "source", "warnings"[], "error"?}
```
- Limits: max upload 50 MB (configurable), 60 s conversion timeout in a worker (ProcessPool — pdfminer can spin), simple IP rate limit (slowapi), CORS allowlist (extension origin `chrome-extension://*` + configured web origins).
- **SSRF guard on /convert/url**: resolve host, block private/link-local ranges, http(s) only, size-capped streaming download. (markitdown fetches URLs happily — we must gate it.)
- Auth: optional single API key header (`X-API-Key`) — enabled when exposed publicly; extension/mobile settings store it.

## Output spec (shared across ALL suite projects)
Front-matter emitted by every product:
```markdown
---
title: <title or filename>
source: <url or filename>
converted: <ISO date>
generator: md-files-dhivalabs/<product>
---
```
Then markitdown's output (ATX headings, pipe tables, 2-newline max). This section is the canonical definition the other plans reference.

## Frontend pages
1. **Converter (home)**: three tabs — Upload (drag-drop + picker, multi-file), URL, YouTube. Result view: rendered preview / raw toggle, Copy, Download .md, "convert another".
2. **Batch**: multiple files → zip of .md results.
3. **Formats page**: auto-generated from `/api/formats`.
4. **Suite page**: links + install instructions for extension, desktop, mobile, MCP connector (this is the "webpage for these features" part — landing page for the whole suite).
- Clean light/dark responsive design; no accounts.

## Architecture
```
backend/
  app/main.py            # FastAPI, routes, limits, CORS
  app/convert.py         # MarkItDown singleton per worker, hints → StreamInfo
  app/security.py        # SSRF guard, api-key, rate limits
  app/youtube.py
  tests/                 # pytest against reference test_files + vectors
frontend/
  src/ (converter tab UI, preview, batch)   → built into backend/static/
Dockerfile, docker-compose.yml, Makefile
```

## Phases
1. **API core** — /convert/file + /convert/url with limits/SSRF guard, pytest suite over upstream test_files, Dockerfile. (This unblocks projects 1 & 2.)
2. **YouTube endpoint + /formats + API key + rate limits.**
3. **Frontend converter page** — upload/URL/YouTube tabs, preview, download; served from container.
4. **Batch + suite landing page + polish** (dark mode, favicon/branding shared with desktop/mobile).
5. **Deploy hardening** — compose file, request logging, max-body config at uvicorn level, README deploy guide.

## Verification
- pytest: every upstream test vector passes through `/api/convert/file`.
- Browser-pane end-to-end: upload pdf/docx, paste URL + YouTube link, check preview and downloaded file.
- SSRF tests: `http://169.254.169.254`, `http://localhost:…`, `file://` all rejected.

## Risks
- Public YouTube transcript fetching gets IP-throttled → clear error + retry advice; consider cookie-less innertube fallback later.
- Long PDF conversions block workers → process pool + timeout is mandatory, not optional.
- Abuse if hosted publicly → API key + rate limit defaults on.
