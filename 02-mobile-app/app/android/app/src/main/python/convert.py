"""Android-side conversion entry points, called from Kotlin via Chaquopy."""

import json
import mimetypes
import os
import sys
from datetime import date

_md = None


def _get_md():
    global _md
    if _md is None:
        sys.setrecursionlimit(20000)
        from markitdown import MarkItDown

        _md = MarkItDown(enable_plugins=False)
    return _md


def _front_matter(title, source):
    lines = ["---"]
    safe = (title or "").replace("\n", " ").strip()
    if safe:
        lines.append(f"title: {safe}")
    lines += [f"source: {source}", f"converted: {date.today().isoformat()}",
              "generator: dhiva-labs/markdrop-mobile", "---"]
    return "\n".join(lines)


def convert_file(path: str) -> str:
    """Convert a local file; returns a JSON string {ok, title, markdown|error}."""
    try:
        from markitdown import StreamInfo

        md = _get_md()
        ext = os.path.splitext(path)[1].lower() or None
        mime, _ = mimetypes.guess_type(path)
        # magika is stubbed on Android, so extension+mimetype hints are the
        # whole guessing story — always pass them.
        with open(path, "rb") as fh:
            result = md.convert_stream(
                fh, stream_info=StreamInfo(
                    extension=ext, mimetype=mime,
                    filename=os.path.basename(path), local_path=path,
                ),
            )
        title = str(result.title) if result.title is not None else None
        body = str(result.markdown).strip()
        doc = f"{_front_matter(title, os.path.basename(path))}\n\n{body}\n"
        return json.dumps({"ok": True, "title": title, "markdown": doc})
    except Exception as e:
        return json.dumps({"ok": False, "error": _friendly_error(e)})


def _friendly_error(e: Exception) -> str:
    detail = str(e).strip() or type(e).__name__
    if "MissingDependencyException" in detail or "dependencies needed" in detail:
        return (
            "This file type isn't supported on this device yet. "
            "PowerPoint files need components that aren't available on the newest "
            "Android memory layout — try the Markdrop web converter instead."
        )
    return f"{type(e).__name__}: {detail[:400]}"


def convert_url(url: str) -> str:
    """Convert a web page / file link / YouTube URL; returns JSON string.

    Fetches with a browser-like User-Agent (default python UA gets 403 from
    Wikipedia and others), then converts the bytes with url-aware StreamInfo
    so the YouTube/Wikipedia specializations still trigger."""
    try:
        import io as _io

        import requests

        from markitdown import StreamInfo

        url = url.strip()
        if not url.startswith(("http://", "https://")):
            return json.dumps({"ok": False, "error": "Only http(s) URLs are supported"})

        md = _get_md()
        resp = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36 Markdrop/0.1",
                "Accept": "text/markdown, text/html;q=0.9, text/plain;q=0.8, */*;q=0.1",
            },
        )
        resp.raise_for_status()

        mime = None
        charset = None
        if "content-type" in resp.headers:
            parts = resp.headers["content-type"].split(";")
            mime = parts.pop(0).strip() or None
            for p in parts:
                p = p.strip()
                if p.startswith("charset="):
                    charset = p.split("=", 1)[1].strip() or None

        filename = None
        ext = None
        tail = resp.url.split("?")[0].rsplit("/", 1)[-1]
        if "." in tail:
            filename = tail
            ext = "." + tail.rsplit(".", 1)[1].lower()

        result = md.convert_stream(
            _io.BytesIO(resp.content),
            stream_info=StreamInfo(
                url=url, mimetype=mime, charset=charset,
                filename=filename, extension=ext,
            ),
        )
        title = str(result.title) if result.title is not None else None
        body = str(result.markdown).strip()
        doc = f"{_front_matter(title, url)}\n\n{body}\n"
        return json.dumps({"ok": True, "title": title, "markdown": doc})
    except Exception as e:
        detail = str(e).strip() or type(e).__name__
        return json.dumps({"ok": False, "error": f"{type(e).__name__}: {detail[:400]}"})


def probe_imports() -> str:
    """Actually import (not find_spec) the risky modules, capturing errors."""
    out = {}
    for mod in ["pdfminer.high_level", "pdfplumber", "cryptography.hazmat.primitives.ciphers",
                "cffi", "lxml.etree", "PIL.Image", "youtube_transcript_api"]:
        try:
            __import__(mod)
            out[mod] = "ok"
        except Exception as e:
            out[mod] = f"{type(e).__name__}: {str(e)[:200]}"
    return json.dumps(out)


def engine_info() -> str:
    """Diagnostics for the spike: python version + which extras import."""
    import importlib.util

    mods = ["markitdown", "bs4", "mammoth", "pptx", "openpyxl", "pdfminer", "lxml", "PIL"]
    state = {m: importlib.util.find_spec(m) is not None for m in mods}
    return json.dumps({"python": sys.version.split()[0], "modules": state})
