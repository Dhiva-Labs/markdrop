# MarkItDown — Full Code Analysis Notes

Analyzed 2026-07-20 from https://github.com/microsoft/markitdown (shallow clone; full source copy kept at `../reference/markitdown/`).

## What it is
Python library + CLI (MIT, Microsoft, "in preview") that converts many file types to LLM-friendly Markdown. Requires Python >= 3.10. Monorepo with 4 packages under `packages/`:

| Package | Purpose |
|---|---|
| `markitdown` | Core library + `markitdown` CLI |
| `markitdown-mcp` | MCP server (`convert_to_markdown(uri)` tool; STDIO default, `--http` for Streamable HTTP + SSE on :3001) |
| `markitdown-ocr` | Plugin: OCR-enhanced PDF/DOCX/PPTX/XLSX converters using LLM vision (OpenAI-compatible client) |
| `markitdown-sample-plugin` | Reference plugin (RTF via striprtf) showing the plugin pattern |

## Core architecture (packages/markitdown/src/markitdown/)
Only ~1,400 lines of core code + ~3,900 lines of converters.

- `_markitdown.py` (806 L) — `MarkItDown` class, the orchestrator. Key flow:
  1. `convert(source)` dispatches by type: str path → `convert_local`, http/https/file/data URI → `convert_uri`, `requests.Response` → `convert_response`, binary stream → `convert_stream`. Everything is normalized to a **seekable BinaryIO** (non-seekable streams are copied into BytesIO; URLs fully buffered in memory).
  2. `_get_stream_info_guesses()` builds a list of `StreamInfo` guesses: base guess from path/headers/kwargs, enhanced via `mimetypes`, plus content-based detection using **magika** (Google ML file-type detector, pinned ~=0.6.1) and **charset_normalizer** for text charset. If magika disagrees with the base guess, both guesses are kept (base first).
  3. `_convert()` — for each guess (plus a final empty StreamInfo), iterate converters **sorted by priority (stable sort, lower value = tried first)**; call `converter.accepts(stream, info, **kwargs)`; if True, call `convert()`. First success wins. Stream position is asserted unchanged after `accepts()` and reset after each attempt. Failures are collected as `FailedConversionAttempt`; if nothing succeeds → `FileConversionException` (had attempts) or `UnsupportedFormatException` (no acceptor).
  4. Output normalization: strip trailing whitespace per line, collapse 3+ newlines to 2.
- Priorities: `PRIORITY_SPECIFIC_FILE_FORMAT = 0.0` (default), `PRIORITY_GENERIC_FILE_FORMAT = 10.0` (PlainText, Zip, Html catch-alls). `register_converter()` **inserts at index 0**, so later registrations win ties. Plugins can pick any priority (e.g. OCR plugin uses -1.0 to pre-empt built-ins).
- `_base_converter.py` — `DocumentConverter` ABC with `accepts()` / `convert()`; `DocumentConverterResult(markdown, title=None)` with soft-deprecated `.text_content` alias and `__str__`.
- `_stream_info.py` — frozen dataclass `StreamInfo(mimetype, extension, charset, filename, local_path, url)` + `copy_and_update()`.
- `_exceptions.py` — `MarkItDownException` → `MissingDependencyException` (optional dep absent; converter skipped), `UnsupportedFormatException`, `FileConversionException(attempts=[FailedConversionAttempt])`.
- `_uri_utils.py` — `parse_data_uri`, `file_uri_to_path`.
- `__main__.py` (281 L) — argparse CLI: stdin or file in, `-o` out, hints `-x/--extension -m/--mime-type -c/--charset`, `-p/--use-plugins`, `--list-plugins`, Azure `-d/--use-docintel -e/--endpoint` and `--use-cu --cu-endpoint --cu-analyzer --cu-file-types`, `--keep-data-uris`.
- HTTP session sends `Accept: text/markdown, text/html;q=0.9, ...` (prefers markdown-for-agents responses).

## Constructor / conversion kwargs
`MarkItDown(enable_builtins=True, enable_plugins=False, requests_session=..., llm_client=..., llm_model=..., llm_prompt=..., exiftool_path=..., style_map=..., docintel_endpoint/credential/file_types/api_version=..., cu_endpoint/credential/analyzer_id/file_types=...)`. The llm/exiftool/style_map globals are injected into every converter's kwargs at convert time (marked TODO: move into converter constructors). `exiftool` is auto-discovered on PATH but only trusted from well-known dirs (/usr/bin etc.) for security.

## Plugin system
- Entry point group **`markitdown.plugin`**; lazy-loaded once into module-global `_plugins`.
- A plugin module exposes `__plugin_interface_version__ = 1` and `register_converters(markitdown, **kwargs)` which calls `markitdown.register_converter(conv, priority=...)`.
- Enabled via `MarkItDown(enable_plugins=True)` or CLI `-p`; MCP server: env `MARKITDOWN_ENABLE_PLUGINS=true`.
- Sample plugin pyproject: `[project.entry-points."markitdown.plugin"] sample_plugin = "markitdown_sample_plugin"`.

## Converters (packages/markitdown/src/markitdown/converters/)
All follow the same pattern: module-level `ACCEPTED_MIME_TYPE_PREFIXES` + `ACCEPTED_FILE_EXTENSIONS`; optional deps imported at module load into `_dependency_exc_info`, re-raised as `MissingDependencyException` in `convert()` with helpful `pip install markitdown[feature]` message.

- **PlainTextConverter** — text/* catch-all (priority 10).
- **HtmlConverter** (priority 10) — BeautifulSoup + `_CustomMarkdownify` (subclass of markdownify.MarkdownConverter): ATX headings, strips javascript: links, escapes URIs, truncates data: URIs unless `keep_data_uris`, checkbox inputs → `[x]`/`[ ]`. Has `convert_string()` helper reused by docx/pptx/etc.
- **ZipConverter** (priority 10) — recursively converts contents via parent MarkItDown instance (takes `markitdown=self`).
- URL-specialized: **RssConverter**, **WikipediaConverter**, **YouTubeConverter** (metadata + youtube-transcript-api), **BingSerpConverter** — these check `stream_info.url` in `accepts()`.
- **DocxConverter** — mammoth → HTML → markdownify; `style_map` supported; `converter_utils/docx/pre_process.py` handles OMML math → LaTeX (`math/omml.py`, `latex_dict.py`).
- **XlsxConverter / XlsConverter** — pandas + openpyxl/xlrd, each sheet → `## SheetName` + `to_html` → md table.
- **PptxConverter** (264 L) — python-pptx: slides, shapes, tables, notes, charts.
- **PdfConverter** (589 L, biggest) — pdfminer.six + **pdfplumber**: table extraction to aligned md tables, form/word-layout heuristics, MasterFormat `.1`-numbering line merge.
- **ImageConverter** — exiftool metadata (ImageSize/Title/.../GPSPosition) + optional LLM caption via `llm_client` (OpenAI-style chat.completions with base64 data URI image).
- **AudioConverter** — exiftool metadata + optional SpeechRecognition (Google) transcription, pydub for format conversion.
- **IpynbConverter**, **CsvConverter**, **EpubConverter**, **OutlookMsgConverter** (olefile), plus:
- **DocumentIntelligenceConverter** (Azure, registered only if `docintel_endpoint` given), **ContentUnderstandingConverter** (570 L, Azure CU, analyzer auto-select by file type). Both registered last → tried first (priority 0, latest insert).

## Dependencies
Core: beautifulsoup4, requests, markdownify, magika~=0.6.1, charset-normalizer, defusedxml.
Optional extras: `[all]`, `[pptx]` python-pptx, `[docx]` mammoth~=1.11.0+lxml, `[xlsx]` pandas+openpyxl, `[xls]` pandas+xlrd, `[pdf]` pdfminer.six>=20251230 + pdfplumber>=0.11.9, `[outlook]` olefile, `[audio-transcription]` pydub+SpeechRecognition, `[youtube-transcription]` youtube-transcript-api~=1.0.0, `[az-doc-intel]`, `[az-content-understanding]`. Build: hatchling/hatch. Docker image available (Dockerfile at repo root).

## markitdown-ocr package (newer, notable)
`LLMVisionOCRService(client, model, default_prompt)` — base64s images, calls OpenAI-compatible vision chat. Subclassed converters `PdfConverterWithOCR` etc. registered at priority **-1.0** so they replace built-ins when plugin enabled. Good template for "enhance built-in converter" plugins.

## Usage snippets
```python
from markitdown import MarkItDown
md = MarkItDown(enable_plugins=False)
print(md.convert("doc.pdf").markdown)          # path, URL, stream, or Response all work
md.convert_uri("https://example.com/x.docx")
# with LLM captions: MarkItDown(llm_client=OpenAI(), llm_model="gpt-4o")
```
CLI: `markitdown file.pdf -o out.md`, `cat x.pdf | markitdown -x .pdf`.
MCP: `markitdown-mcp` (stdio) or `markitdown-mcp --http --host 127.0.0.1 --port 3001` (no auth — localhost only warning built in).

## Key design takeaways for our project
1. **Priority-ordered converter chain + accepts()/convert() protocol** — clean, pluggable, first-success-wins with graceful fallback across multiple stream-info guesses.
2. **Everything is a seekable binary stream** with strict position discipline (assertions enforce it).
3. **StreamInfo guesses** decouple "what is this file" from "how to convert it"; magika content sniffing beats trusting extensions.
4. Optional deps degrade gracefully (skip converter, raise helpful install hint only if it was the only candidate).
5. Plugins = entry points + priority numbers; negative priority overrides built-ins.
6. Test harness uses declarative "test vectors" (`tests/_test_vectors.py`: file + expected `must_include` strings) shared by CLI and module tests — nice pattern to copy.

## Gotchas
- URLs/responses fully buffered in memory (no size cap) — mind huge files.
- magika 0.6.x pinned; ships an ML model, adds noticeable install size/startup cost.
- `register_converter` inserting at index 0 means registration ORDER matters within same priority (most recent wins).
- `accepts()` must not move the stream position (asserted at runtime).
- Output markdown title is often None; only some converters set it.
- exiftool path only auto-accepted from allowlisted directories.
