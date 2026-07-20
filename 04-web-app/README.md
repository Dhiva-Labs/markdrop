# MD Converter Web (+ shared Conversion API)

FastAPI service wrapping [MarkItDown](https://github.com/microsoft/markitdown) with a self-contained web frontend. Also serves as the shared Conversion API for the browser extension (project 01) and mobile app (project 02).

## Run (dev)
```bash
cd backend
uv venv .venv && uv pip install -p .venv/bin/python -r requirements.txt
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8460 --reload
# open http://127.0.0.1:8460
```

## Run (Docker)
```bash
docker build -t md-converter .
docker run -p 8000:8000 -e MD_API_KEY=changeme md-converter
```

## API
| Endpoint | Body | Notes |
|---|---|---|
| `POST /api/convert/file` | multipart `file` (+ optional `extension`, `mimetype`, `charset` form fields) | 50 MB cap |
| `POST /api/convert/url` | `{"url": "..."}` | SSRF-guarded, redirects re-validated, 50 MB cap |
| `POST /api/convert/youtube` | `{"url": "..."}` | metadata + transcript |
| `GET /api/formats` | — | live extras report |
| `GET /api/health` | — | |

All success responses: `{"ok": true, "title", "markdown", "source", "warnings"}` — markdown includes the suite's standard front-matter (title/source/converted/generator).

## Configuration (env vars)
| Var | Default | Meaning |
|---|---|---|
| `MD_API_KEY` | *(empty = auth off)* | require `X-API-Key` header |
| `MD_MAX_UPLOAD_BYTES` / `MD_MAX_DOWNLOAD_BYTES` | 50 MB | size caps |
| `MD_CONVERT_TIMEOUT` | 60 s | per-conversion timeout (worker pool recycled on timeout) |
| `MD_WORKERS` | 2 | conversion process pool size |
| `MD_RATE_PER_MINUTE` / `MD_RATE_BURST` | 30 / 10 | per-IP token bucket |
| `MD_CORS_ORIGINS` | `*` | comma-separated allowlist |
| `MD_ALLOW_PRIVATE_URLS` | off | disable SSRF guard (dev only) |
| `MD_FETCH_TIMEOUT` | 30 s | outbound fetch timeout |

## Tests
```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```
Vectors run real conversions over the upstream markitdown test files (`../reference/markitdown/.../test_files`).

## Implementation notes
- Conversions run in a `ProcessPoolExecutor`; each worker keeps a warm `MarkItDown` and a raised recursion limit (deep HTML like Wikipedia needs it). Only plain strings cross the process boundary — markitdown exceptions/titles can reference unpicklable parse trees (`WorkerConversionError`, str coercion).
- URL fetching does manual redirect hops so every hop is validated against private/reserved IP ranges.
