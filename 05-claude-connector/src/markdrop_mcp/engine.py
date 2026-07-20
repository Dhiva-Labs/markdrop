"""Conversion engine: warm MarkItDown instance + output shaping for MCP."""

import io
import os
import re
import sys
from datetime import date
from pathlib import Path

from .security import Roots, fetch_url_safe

MAX_INLINE_CHARS = int(os.getenv("MD_MCP_MAX_INLINE_CHARS", "100000"))

_md = None


def get_md():
    global _md
    if _md is None:
        # Deep HTML (e.g. Wikipedia) overflows the default recursion limit
        # inside BeautifulSoup/markdownify.
        sys.setrecursionlimit(20000)
        from markitdown import MarkItDown

        _md = MarkItDown(enable_plugins=False)
    return _md


def front_matter(*, title: str | None, source: str) -> str:
    safe_title = (title or "").replace("\n", " ").strip()
    lines = ["---"]
    if safe_title:
        lines.append(f"title: {safe_title}")
    lines.append(f"source: {source}")
    lines.append(f"converted: {date.today().isoformat()}")
    lines.append("generator: dhiva-labs/markdrop-mcp")
    lines.append("---")
    return "\n".join(lines)


def shape_output(
    *,
    title: str | None,
    markdown: str,
    source: str,
    output_path: Path | None = None,
) -> str:
    """Assemble final markdown; write to disk if requested; cap what is
    returned inline so huge documents don't flood Claude's context."""
    full = f"{front_matter(title=title, source=source)}\n\n{markdown.strip()}\n"

    notice = ""
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full, encoding="utf-8")
        notice = f"[Saved {len(full):,} characters to {output_path}]\n\n"

    if len(full) > MAX_INLINE_CHARS:
        if output_path is None:
            notice = (
                f"[Output is {len(full):,} characters; showing the first "
                f"{MAX_INLINE_CHARS:,}. Call the tool again with an output_path "
                "to save the complete document.]\n\n"
            )
        else:
            notice += (
                f"[Showing the first {MAX_INLINE_CHARS:,} characters; "
                "the file on disk is complete.]\n\n"
            )
        full = full[:MAX_INLINE_CHARS]

    return notice + full


def convert_stream_bytes(
    data: bytes,
    *,
    filename: str | None = None,
    extension: str | None = None,
    mimetype: str | None = None,
    charset: str | None = None,
    url: str | None = None,
) -> tuple[str | None, str]:
    from markitdown import StreamInfo

    md = get_md()
    result = md.convert_stream(
        io.BytesIO(data),
        stream_info=StreamInfo(
            filename=filename, extension=extension, mimetype=mimetype,
            charset=charset, url=url,
        ),
    )
    # Coerce to plain builtins (titles can be bs4 NavigableString)
    title = str(result.title) if result.title is not None else None
    return title, str(result.markdown)


def convert_local_file(path: Path) -> tuple[str | None, str]:
    md = get_md()
    result = md.convert_local(path)
    title = str(result.title) if result.title is not None else None
    return title, str(result.markdown)


def convert_remote_url(url: str) -> tuple[str | None, str]:
    """SSRF-guarded URL conversion (markitdown's own fetcher is not guarded)."""
    fetched = fetch_url_safe(url)
    extension = None
    filename = fetched.filename
    if filename and "." in filename:
        extension = "." + filename.rsplit(".", 1)[1].lower()
    else:
        from urllib.parse import urlparse

        tail = urlparse(fetched.url).path.rsplit("/", 1)[-1]
        if "." in tail:
            filename = tail
            extension = "." + tail.rsplit(".", 1)[1].lower()
    return convert_stream_bytes(
        fetched.data,
        filename=filename,
        extension=extension,
        mimetype=fetched.mimetype,
        charset=fetched.charset,
        url=url,
    )


YOUTUBE_URL_RE = re.compile(
    r"^https?://(www\.|m\.)?(youtube\.com/(watch\?|shorts/)|youtu\.be/)", re.IGNORECASE
)

VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})")


def timestamped_transcript(url: str) -> str:
    """Timestamped transcript via youtube-transcript-api (markitdown's YouTube
    converter emits plain text only)."""
    m = VIDEO_ID_RE.search(url)
    if not m:
        raise ValueError("Could not find a video id in the URL")
    from youtube_transcript_api import YouTubeTranscriptApi

    fetched = YouTubeTranscriptApi().fetch(m.group(1))
    lines = []
    for snippet in fetched:
        total = int(snippet.start)
        stamp = f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"
        text = snippet.text.replace("\n", " ").strip()
        if text:
            lines.append(f"[{stamp}] {text}")
    return "\n".join(lines)


# Extensions convert_directory will attempt (mirrors installed converters)
CONVERTIBLE_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".xls", ".pptx", ".epub", ".ipynb", ".msg",
    ".html", ".htm", ".csv", ".json", ".xml", ".txt", ".md", ".zip",
    ".jpg", ".jpeg", ".png", ".mp3", ".wav", ".m4a",
}
