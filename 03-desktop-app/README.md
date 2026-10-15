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

# app (Flutter does not cross-compile Linux: build on the architecture you want)
cd ../app && flutter build linux --release
./build/linux/x64/release/bundle/md_converter_desktop      # on arm64: build/linux/arm64/release/bundle/
```

The engine tests read markitdown's own test files from
`reference/markitdown/packages/markitdown/tests/test_files` (git-ignored; CI fetches them from the
matching markitdown tag).

## Packaging (.deb for amd64 and arm64)
`packaging/build_deb.sh` assembles `markdrop-studio_<version>_<arch>.deb` from `engine/dist/md-engine/`
and `app/build/linux/<x64|arm64>/release/bundle/`. The architecture comes from `dpkg
--print-architecture`, so build the engine and the app on the machine you package on. The package
version is in `packaging/deb-version`; layout:

```
/opt/markdrop-studio/{md_converter_desktop,lib,data,md-engine,icon.png}
/usr/bin/markdrop -> /opt/markdrop-studio/md_converter_desktop
/usr/share/applications/markdrop-studio.desktop
```

```bash
packaging/build_deb.sh dist           # writes dist/markdrop-studio_<version>_<arch>.deb
xvfb-run -a markdrop --selftest some.docx   # headless check of the installed package
```

CI (`.github/workflows/studio-linux.yml`) does exactly this on `ubuntu-24.04` and `ubuntu-24.04-arm`,
and on a published release attaches the `.deb` files that are not on it yet. To add them to a
release that already exists, run the workflow by hand and give it the tag (`release_tag`).

## Features (v0.1)
- Drop zone + file picker, URL/YouTube box, serial batch queue with per-job status.
- Preview pane: rendered (flutter_markdown) / raw toggle, copy, save-as .md.
- Engine status in the app bar; failures show the converter error inline.
- **Headless self-test** for CI/agents: `md_converter_desktop --selftest <file>` converts through the real sidecar, prints JSON, exits (verified: docx → 4,803 chars).

## Packaging status
The `.deb` for amd64 and arm64 is built in CI (see above). Still open: AppImage, and Windows/macOS builds.

## Remaining (per PLAN.md)
Watch folders, clipboard watcher, output-folder batch export, AppImage packaging, Win/mac CI builds.
