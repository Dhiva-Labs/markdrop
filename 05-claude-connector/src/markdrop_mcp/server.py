"""MCP tools for the md-files-dhivalabs conversion suite."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import engine
from .security import Roots

mcp = FastMCP("markdrop")

# Configured by __main__ before run; default allows cwd/Documents/Downloads
roots = Roots()


def _out_path(output_path: str | None, default_for: Path | None = None) -> Path | None:
    if output_path is not None:
        return roots.resolve(output_path)
    if default_for is not None:
        return default_for.with_suffix(".md")
    return None


@mcp.tool()
def convert_file(path: str, output_path: str | None = None) -> str:
    """Convert a local file (pdf, docx, xlsx, pptx, epub, html, csv, ipynb,
    msg, zip, images, audio, ...) to Markdown. Optionally write the result to
    output_path (defaults to returning it inline; large outputs are truncated
    inline, so pass output_path for big documents)."""
    src = roots.resolve(path)
    if not src.is_file():
        raise FileNotFoundError(f"No such file: {src}")
    title, markdown = engine.convert_local_file(src)
    out = _out_path(output_path)
    return engine.shape_output(title=title, markdown=markdown, source=str(src), output_path=out)


@mcp.tool()
def convert_url(url: str, output_path: str | None = None) -> str:
    """Fetch an http(s) URL (web page, or a direct link to a pdf/docx/etc.)
    and convert it to Markdown. Wikipedia, RSS and YouTube URLs get special
    handling automatically."""
    title, markdown = engine.convert_remote_url(url)
    out = _out_path(output_path)
    return engine.shape_output(title=title, markdown=markdown, source=url, output_path=out)


@mcp.tool()
def convert_to_markdown(uri: str) -> str:
    """Convert a resource described by a file:, http:, https: or data: URI to
    Markdown (compatibility tool, mirrors Microsoft's markitdown-mcp)."""
    uri = uri.strip()
    if uri.startswith("file:"):
        from urllib.request import url2pathname
        from urllib.parse import urlparse

        parsed = urlparse(uri)
        return convert_file(url2pathname(parsed.path))
    if uri.startswith(("http:", "https:")):
        return convert_url(uri)
    if uri.startswith("data:"):
        md = engine.get_md()
        result = md.convert_uri(uri)
        title = str(result.title) if result.title is not None else None
        return engine.shape_output(title=title, markdown=str(result.markdown), source="data: URI")
    raise ValueError("Unsupported URI scheme; use file:, http:, https:, or data:")


@mcp.tool()
def youtube_to_markdown(url: str, include_timestamps: bool = False, output_path: str | None = None) -> str:
    """Convert a YouTube video to Markdown: title, channel, description and
    transcript. Set include_timestamps=true for a [hh:mm:ss]-stamped transcript."""
    if not engine.YOUTUBE_URL_RE.match(url.strip()):
        raise ValueError("Not a recognized YouTube watch/shorts URL")
    title, markdown = engine.convert_remote_url(url)
    if include_timestamps:
        try:
            stamped = engine.timestamped_transcript(url)
            markdown += "\n\n### Timestamped Transcript\n" + stamped
        except Exception as e:
            markdown += f"\n\n*(Timestamped transcript unavailable: {e})*"
    out = _out_path(output_path)
    return engine.shape_output(title=title, markdown=markdown, source=url, output_path=out)


@mcp.tool()
def convert_directory(path: str, glob: str = "*", output_dir: str | None = None) -> str:
    """Batch-convert every supported file in a directory to Markdown files.
    glob supports patterns like '*.pdf' or '**/*.docx' (recursive). Results are
    written next to the sources, or into output_dir. Returns a summary."""
    src_dir = roots.resolve(path)
    if not src_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {src_dir}")
    out_dir = roots.resolve(output_dir) if output_dir else None

    files = [
        f for f in sorted(src_dir.glob(glob))
        if f.is_file() and f.suffix.lower() in engine.CONVERTIBLE_EXTENSIONS
        and f.suffix.lower() != ".md"
    ][:200]
    if not files:
        return f"No convertible files matched {glob!r} in {src_dir}"

    ok, failed = [], []
    for f in files:
        try:
            title, markdown = engine.convert_local_file(f)
            target = (out_dir / f.with_suffix(".md").name) if out_dir else f.with_suffix(".md")
            engine.shape_output(title=title, markdown=markdown, source=str(f), output_path=target)
            ok.append(f"{f.name} -> {target}")
        except Exception as e:
            failed.append(f"{f.name}: {type(e).__name__}: {str(e)[:200]}")

    lines = [f"Converted {len(ok)}/{len(files)} files from {src_dir}:"]
    lines += [f"  ✓ {line}" for line in ok]
    if failed:
        lines.append("Failures:")
        lines += [f"  ✗ {line}" for line in failed]
    return "\n".join(lines)


@mcp.tool()
def list_supported_formats() -> str:
    """List the file formats this converter supports and the allowed file roots."""
    import importlib.util

    extras = {
        "pdf": "pdfminer", "docx": "mammoth", "xlsx": "openpyxl", "xls": "xlrd",
        "pptx": "pptx", "outlook-msg": "olefile",
        "youtube-transcripts": "youtube_transcript_api",
        "audio-transcription": "speech_recognition",
    }
    lines = ["Always available: text, html, csv, json, xml, ipynb, epub, zip, rss/atom, wikipedia, youtube metadata, image/audio metadata."]
    for name, mod in extras.items():
        state = "yes" if importlib.util.find_spec(mod) else "NOT installed"
        lines.append(f"- {name}: {state}")
    lines.append(f"Allowed file roots: {roots.describe()}")
    return "\n".join(lines)
