import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from . import convert, security

MAX_UPLOAD_BYTES = int(os.getenv("MD_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

YOUTUBE_URL_RE = re.compile(
    r"^https?://(www\.|m\.)?(youtube\.com/(watch\?|shorts/)|youtu\.be/)", re.IGNORECASE
)

limiter = security.RateLimiter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    convert.shutdown_executor()


app = FastAPI(title="Markdrop API (Dhiva Labs)", version="0.1.0", lifespan=lifespan)

cors_origins = [o for o in os.getenv("MD_CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class UrlRequest(BaseModel):
    url: str


def _gate(request: Request, x_api_key: str | None) -> None:
    if not security.api_key_ok(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded; slow down")


def _ok(*, title: str | None, markdown: str, source: str, warnings: list[str] | None = None):
    fm = convert.front_matter(title=title, source=source)
    return {
        "ok": True,
        "title": title,
        "markdown": f"{fm}\n\n{markdown.strip()}\n",
        "source": source,
        "warnings": warnings or [],
    }


def _conversion_error(e: Exception) -> JSONResponse:
    if isinstance(e, convert.ConversionTimeout):
        return JSONResponse(status_code=504, content={"ok": False, "error": str(e)})
    if isinstance(e, convert.WorkerConversionError) and e.unsupported:
        return JSONResponse(
            status_code=415,
            content={"ok": False, "error": "Unsupported file type: no converter could handle this input."},
        )
    return JSONResponse(
        status_code=422,
        content={"ok": False, "error": f"Conversion failed: {e}"},
    )


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "md-converter", "version": app.version}


@app.get("/api/formats")
async def formats():
    import importlib.util

    extras = {
        "pdf": "pdfminer",
        "docx": "mammoth",
        "xlsx": "openpyxl",
        "xls": "xlrd",
        "pptx": "pptx",
        "outlook": "olefile",
        "audio-transcription": "speech_recognition",
        "youtube-transcription": "youtube_transcript_api",
    }
    live = {name: importlib.util.find_spec(mod) is not None for name, mod in extras.items()}
    always = ["txt/text", "html", "csv", "json", "xml", "ipynb", "epub", "zip", "rss/atom", "wikipedia", "youtube-metadata", "image-metadata", "audio-metadata"]
    return {"ok": True, "always": always, "extras": live}


@app.post("/api/convert/file")
async def convert_file(
    request: Request,
    file: UploadFile = File(...),
    extension: str | None = Form(default=None),
    mimetype: str | None = Form(default=None),
    charset: str | None = Form(default=None),
    x_api_key: str | None = Header(default=None),
):
    _gate(request, x_api_key)

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_BYTES} bytes")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty upload")

    filename = file.filename or None
    ext = extension
    if ext is None and filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[1].lower()
    elif ext is not None and not ext.startswith("."):
        ext = "." + ext

    try:
        outcome = await convert.convert_bytes_async(
            data,
            filename=filename,
            extension=ext,
            mimetype=mimetype or (file.content_type if file.content_type != "application/octet-stream" else None),
            charset=charset,
        )
    except Exception as e:
        return _conversion_error(e)

    return _ok(
        title=outcome.title or (filename.rsplit(".", 1)[0] if filename else None),
        markdown=outcome.markdown,
        source=filename or "upload",
    )


async def _convert_remote(request: Request, url: str, x_api_key: str | None):
    _gate(request, x_api_key)
    try:
        fetched = security.fetch_url_safe(url)
    except security.UnsafeUrlError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except security.DownloadTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch URL: {e}")

    filename = fetched.filename
    extension = None
    if filename and "." in filename:
        extension = "." + filename.rsplit(".", 1)[1].lower()
    else:
        from urllib.parse import urlparse

        path = urlparse(fetched.url).path
        if "." in path.rsplit("/", 1)[-1]:
            extension = "." + path.rsplit(".", 1)[1].lower()
            filename = path.rsplit("/", 1)[-1]

    try:
        outcome = await convert.convert_bytes_async(
            fetched.data,
            filename=filename,
            extension=extension,
            mimetype=fetched.mimetype,
            charset=fetched.charset,
            url=url,
        )
    except Exception as e:
        return _conversion_error(e)

    return _ok(title=outcome.title, markdown=outcome.markdown, source=url)


@app.post("/api/convert/url")
async def convert_url(request: Request, body: UrlRequest, x_api_key: str | None = Header(default=None)):
    return await _convert_remote(request, body.url, x_api_key)


@app.post("/api/convert/youtube")
async def convert_youtube(request: Request, body: UrlRequest, x_api_key: str | None = Header(default=None)):
    if not YOUTUBE_URL_RE.match(body.url.strip()):
        raise HTTPException(status_code=400, detail="Not a recognized YouTube watch/shorts URL")
    return await _convert_remote(request, body.url, x_api_key)


# --- Static frontend ---------------------------------------------------------

@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


from fastapi.staticfiles import StaticFiles  # noqa: E402

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
