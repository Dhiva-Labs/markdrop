# MD Converter Desktop (Linux / Windows / macOS)

Flutter desktop app + PyInstaller-frozen markitdown sidecar. Drag-and-drop batch conversion with rendered preview.

## Layout
- `engine/` — `md_engine.py`: JSON wrapper over markitdown. One-shot (`convert <src> [-o file]`), warm stdio server (`serve`: line-delimited JSON, `{"id","cmd":"convert","source",...}`), `formats`. Frozen with PyInstaller → `engine/dist/md-engine/` (~181 MB, includes magika model).
- `app/` — Flutter app. `lib/engine/sidecar.dart` finds the engine (env `MD_ENGINE` → bundled next to exe → dev-tree paths), speaks the stdio protocol with per-request timeouts and auto-restart on exit. `lib/engine/jobs.dart` is the serial job queue.

## Build & run
```bash
# engine
cd engine && uv venv .venv && uv pip install -p .venv/bin/python "markitdown[pdf,docx,pptx,xlsx,xls,outlook,youtube-transcription]" pyinstaller pytest
.venv/bin/python -m pytest test_engine.py -q         # 4 golden tests
.venv/bin/pyinstaller --noconfirm --onedir --name md-engine \
  --collect-all magika --collect-data pdfminer --collect-data olefile md_engine.py

# app
cd ../app && flutter build linux --release
./build/linux/x64/release/bundle/md_converter_desktop
```

## Features (v0.1)
- Drop zone + file picker, URL/YouTube box, serial batch queue with per-job status.
- Preview pane: rendered (flutter_markdown) / raw toggle, copy, save-as .md.
- Engine status in the app bar; failures show the converter error inline.
- **Headless self-test** for CI/agents: `md_converter_desktop --selftest <file>` converts through the real sidecar, prints JSON, exits (verified: docx → 4,803 chars).

## Packaging plan (pending)
Bundle `engine/dist/md-engine/` next to the app binary as `md-engine/` (sidecar looks there first), then .deb/AppImage; Windows/mac via CI — untested locally.

## Remaining (per PLAN.md)
Watch folders, clipboard watcher, output-folder batch export, .deb/AppImage packaging, Win/mac CI builds.
