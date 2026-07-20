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
        detail = str(e).strip() or type(e).__name__
        return json.dumps({"ok": False, "error": f"{type(e).__name__}: {detail[:400]}"})


def engine_info() -> str:
    """Diagnostics for the spike: python version + which extras import."""
    import importlib.util

    mods = ["markitdown", "bs4", "mammoth", "pptx", "openpyxl", "pdfminer", "lxml", "PIL"]
    state = {m: importlib.util.find_spec(m) is not None for m in mods}
    return json.dumps({"python": sys.version.split()[0], "modules": state})
