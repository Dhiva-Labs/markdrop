"""Conversion workers: markitdown runs in a process pool so slow/hung conversions
can't stall the event loop, and each worker keeps a warm MarkItDown instance."""

import asyncio
import io
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import date

CONVERT_TIMEOUT = int(os.getenv("MD_CONVERT_TIMEOUT", "60"))
_WORKERS = int(os.getenv("MD_WORKERS", "2"))

_md = None  # per-worker-process singleton


def _get_md():
    global _md
    if _md is None:
        import sys

        from markitdown import MarkItDown

        # Deeply nested HTML (e.g. Wikipedia) overflows the default 1000-frame
        # recursion limit inside BeautifulSoup/markdownify.
        sys.setrecursionlimit(20000)
        _md = MarkItDown(enable_plugins=False)
    return _md


@dataclass
class ConversionOutcome:
    title: str | None
    markdown: str


class WorkerConversionError(Exception):
    """Picklable stand-in for whatever the converter raised. markitdown's
    exceptions can hold tracebacks/parse trees that cannot cross the process
    boundary, so only flat strings leave the worker."""

    def __init__(self, message: str, unsupported: bool = False):
        super().__init__(message)
        self.unsupported = unsupported

    def __reduce__(self):
        return (WorkerConversionError, (self.args[0], self.unsupported))


def _convert_bytes(
    data: bytes,
    *,
    filename: str | None = None,
    extension: str | None = None,
    mimetype: str | None = None,
    charset: str | None = None,
    url: str | None = None,
) -> tuple[str | None, str]:
    """Runs inside a worker process. Returns (title, markdown) as plain values."""
    import traceback

    from markitdown import StreamInfo, UnsupportedFormatException

    md = _get_md()
    info = StreamInfo(
        filename=filename,
        extension=extension,
        mimetype=mimetype,
        charset=charset,
        url=url,
    )
    try:
        result = md.convert_stream(io.BytesIO(data), stream_info=info)
        # Force plain builtins: converters may return str subclasses (e.g. bs4
        # NavigableString) that drag entire parse trees through pickle.
        title = str(result.title) if result.title is not None else None
        return (title, str(result.markdown))
    except UnsupportedFormatException as e:
        raise WorkerConversionError(str(e), unsupported=True) from None
    except Exception as e:
        detail = str(e).strip() or type(e).__name__
        tb_last = traceback.format_exc(limit=-3)
        raise WorkerConversionError(f"{type(e).__name__}: {detail}\n{tb_last}") from None


_executor: ProcessPoolExecutor | None = None


def get_executor() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(max_workers=_WORKERS)
    return _executor


def shutdown_executor() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None


class ConversionTimeout(Exception):
    pass


async def convert_bytes_async(data: bytes, **hints) -> ConversionOutcome:
    future = get_executor().submit(_convert_bytes, data, **hints)
    try:
        title, markdown = await asyncio.wait_for(
            asyncio.wrap_future(future), CONVERT_TIMEOUT
        )
        return ConversionOutcome(title=title, markdown=markdown)
    except asyncio.TimeoutError:
        future.cancel()
        # The worker may be stuck mid-conversion; recycle the pool so it can't
        # poison subsequent requests.
        shutdown_executor()
        raise ConversionTimeout(f"Conversion exceeded {CONVERT_TIMEOUT}s") from None


def front_matter(*, title: str | None, source: str, generator: str = "md-files-dhivalabs/web") -> str:
    safe_title = (title or "").replace("\n", " ").strip()
    lines = ["---"]
    if safe_title:
        lines.append(f"title: {safe_title}")
    lines.append(f"source: {source}")
    lines.append(f"converted: {date.today().isoformat()}")
    lines.append(f"generator: {generator}")
    lines.append("---")
    return "\n".join(lines)
