#!/usr/bin/env python3
"""md-engine: JSON wrapper around markitdown for the desktop app sidecar.

Modes:
  md_engine.py convert <path-or-url> [--output FILE]   one-shot, JSON on stdout
  md_engine.py serve                                    stdio server: one JSON
      request per line -> one JSON response per line (keeps Python warm)
  md_engine.py formats                                  supported formats JSON

Request (serve mode):  {"id": 1, "cmd": "convert", "source": "...", "output": "...?"}
Response:              {"id": 1, "ok": true, "title": ..., "markdown": ..., "source": ...}
                       {"id": 1, "ok": false, "error": "..."}
"""

import argparse
import io
import json
import sys
import traceback
from datetime import date
from pathlib import Path

_md = None


def get_md():
    global _md
    if _md is None:
        sys.setrecursionlimit(20000)  # deep HTML (e.g. Wikipedia)
        from markitdown import MarkItDown

        _md = MarkItDown(enable_plugins=False)
    return _md


def front_matter(title, source):
    lines = ["---"]
    safe = (title or "").replace("\n", " ").strip()
    if safe:
        lines.append(f"title: {safe}")
    lines += [f"source: {source}", f"converted: {date.today().isoformat()}",
              "generator: dhiva-labs/markdrop-desktop", "---"]
    return "\n".join(lines)


def do_convert(source: str, output: str | None = None) -> dict:
    md = get_md()
    try:
        if source.startswith(("http:", "https:")):
            result = md.convert_uri(source)
            src_label = source
        else:
            path = Path(source).expanduser()
            if not path.is_file():
                return {"ok": False, "error": f"No such file: {path}"}
            result = md.convert_local(str(path))
            src_label = str(path)
        # plain builtins only (titles can be bs4 NavigableString)
        title = str(result.title) if result.title is not None else None
        body = str(result.markdown).strip()
        doc = f"{front_matter(title, src_label)}\n\n{body}\n"
        resp = {"ok": True, "title": title, "source": src_label, "chars": len(doc)}
        if output:
            out = Path(output).expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(doc, encoding="utf-8")
            resp["output"] = str(out)
        else:
            resp["markdown"] = doc
        return resp
    except Exception as e:
        from markitdown import UnsupportedFormatException

        if isinstance(e, UnsupportedFormatException):
            return {"ok": False, "error": "Unsupported file type", "unsupported": True}
        detail = str(e).strip() or type(e).__name__
        return {"ok": False, "error": f"{type(e).__name__}: {detail[:500]}"}


def do_formats() -> dict:
    import importlib.util

    extras = {
        "pdf": "pdfminer", "docx": "mammoth", "xlsx": "openpyxl", "xls": "xlrd",
        "pptx": "pptx", "outlook": "olefile", "youtube": "youtube_transcript_api",
    }
    return {
        "ok": True,
        "always": ["txt", "html", "csv", "json", "xml", "ipynb", "epub", "zip", "rss",
                   "wikipedia", "image-metadata", "audio-metadata"],
        "extras": {k: importlib.util.find_spec(m) is not None for k, m in extras.items()},
    }


def serve() -> None:
    """Line-delimited JSON over stdio. Warm instance survives across requests."""
    get_md()  # warm up before signalling readiness
    print(json.dumps({"ready": True}), flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            print(json.dumps({"ok": False, "error": f"bad json: {e}"}), flush=True)
            continue
        rid = req.get("id")
        cmd = req.get("cmd")
        try:
            if cmd == "convert":
                resp = do_convert(req.get("source", ""), req.get("output"))
            elif cmd == "formats":
                resp = do_formats()
            elif cmd == "ping":
                resp = {"ok": True, "pong": True}
            elif cmd == "quit":
                print(json.dumps({"id": rid, "ok": True, "bye": True}), flush=True)
                return
            else:
                resp = {"ok": False, "error": f"unknown cmd: {cmd}"}
        except Exception:
            resp = {"ok": False, "error": traceback.format_exc()[-500:]}
        resp["id"] = rid
        print(json.dumps(resp), flush=True)


def main():
    parser = argparse.ArgumentParser(prog="md-engine")
    sub = parser.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("convert")
    c.add_argument("source")
    c.add_argument("--output", "-o", default=None)
    sub.add_parser("serve")
    sub.add_parser("formats")
    args = parser.parse_args()

    if args.mode == "convert":
        print(json.dumps(do_convert(args.source, args.output)))
    elif args.mode == "formats":
        print(json.dumps(do_formats()))
    elif args.mode == "serve":
        serve()


if __name__ == "__main__":
    main()
