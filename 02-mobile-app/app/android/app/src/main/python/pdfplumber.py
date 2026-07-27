"""Stub for pdfplumber (real package needs pypdfium2, unavailable on Android).

markitdown's PdfConverter imports pdfplumber at module load, then wraps ALL
pdfplumber usage in try/except with a full pdfminer fallback. This stub lets
the import succeed and makes every open() raise, so PDFs are extracted with
pdfminer's text engine (no tables, but full text)."""


class PdfplumberUnavailable(RuntimeError):
    pass


def open(*args, **kwargs):  # noqa: A001 - mirrors pdfplumber's API
    raise PdfplumberUnavailable(
        "pdfplumber is not available on Android; using pdfminer fallback"
    )
