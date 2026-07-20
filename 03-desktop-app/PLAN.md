# Project 3 — MD Converter Desktop (Linux / Windows / macOS)

Drag-and-drop desktop app: drop any files/URLs → Markdown, with batch queue, side-by-side preview, and watch folders.

## Stack
- **Flutter desktop** (your proven stack: DeltaView, MockStudio, Rover Explorer…).
- **Engine: markitdown as a bundled sidecar binary** built with **PyInstaller** (`markitdown[all]` + youtube-transcript-api, one-folder build). Flutter spawns it per job:
  - `md-engine convert <path|url> [--json]` → returns JSON `{markdown, title, error}` on stdout.
  - Sidecar is our own thin CLI wrapper (`engine/md_engine.py`) around the markitdown API — gives us JSON output, batch stdin mode (`--serve-stdio`: one JSON request per line, keeps Python warm so repeated conversions skip cold start).
- Fallback when sidecar missing (dev mode): call system `python3 -m markitdown` if available.
- Optional LLM captioning: settings field for OpenAI-compatible key → passed to sidecar env. Off by default.

## Features

### MVP (Phase 1–3)
1. **Drop zone**: drag files/folders/URLs onto window (desktop_drop), or click to pick; multi-file batch queue with per-item status/progress.
2. **All markitdown formats**: pdf, docx, xlsx/xls, pptx, epub, ipynb, msg, html, csv, zip, images (exif), audio (metadata; transcription when configured), URLs (pages, Wikipedia/YouTube/RSS specializations).
3. **YouTube box**: paste link → transcript md (same UX promise as extension/mobile).
4. **Preview pane**: source-info left, rendered Markdown right (flutter_markdown), raw/rendered toggle, copy button.
5. **Export**: save single .md, batch export to chosen folder (mirrors input names), "open in default editor".
6. **Settings**: output folder, filename template, front-matter on/off, keep-data-uris, LLM key (optional), sidecar path override.

### v2 (Phase 4+)
7. **Watch folders**: monitor a directory; new files auto-convert into an output dir (great for a "drop PDFs here" workflow).
8. **Clipboard watcher**: copied URL → toast "Convert to MD?".
9. CLI companion (`mdconv file.pdf`) shipping in the same package; file-manager "Open with" registration (.desktop on Linux, registry on Windows).
10. Packaging: **Linux .deb + AppImage** (build on this machine), **Windows** zip/inno via CI or manual on a Windows box, **macOS** .app via CI (GitHub Actions matrix) — mac untested locally, marked experimental like other projects.

## Architecture
```
app/ (Flutter)
  lib/engine/sidecar.dart      # spawn/serve-stdio protocol, job queue, timeouts
  lib/engine/jobs.dart         # batch model, statuses, cancellation
  lib/screens/ (home dropzone, queue, viewer, settings, watch-folders)
engine/ (Python)
  md_engine.py                 # JSON CLI + stdio server wrapper over markitdown
  build.spec                   # PyInstaller spec per-OS
dist/                          # packaged outputs (like api_workbench convention)
```
- Sidecar discovery order: bundled path → settings override → PATH.
- Every job runs with a timeout + captured stderr surfaced in the UI on failure (converter attempt list from `FileConversionException` shown verbatim — it's informative).

## Phases
1. **Engine sidecar** — write `md_engine.py` (single + stdio-serve modes), PyInstaller Linux build, golden tests against markitdown test_files. This de-risks everything.
2. **Flutter shell** — dropzone, queue, sidecar integration, preview pane, save/export, settings.
3. **YouTube/URL flow + polish** — link box, error UX, front-matter, filename templates, app icon/branding consistent with suite.
4. **Watch folders + clipboard watcher.**
5. **Packaging** — .deb + AppImage locally (snap-Flutter gotchas noted in luna-media-player memory), GitHub Actions matrix for Win/mac artifacts.

## Verification
- Golden tests: run sidecar over `reference/markitdown/.../test_files/`, compare to expected-substring vectors.
- Linux end-to-end verified locally (launch app, drop pdf/docx/xlsx, check preview + export). Windows/mac builds marked untested unless CI proves them.

## Risks
- PyInstaller + magika (onnxruntime, model data files) needs explicit `--collect-all magika` etc.; size ~150–250 MB — acceptable for desktop.
- exiftool is an external binary: bundle per-OS or degrade gracefully (markitdown already degrades).
- Windows/mac: no local hardware → CI builds only, flag as experimental.
