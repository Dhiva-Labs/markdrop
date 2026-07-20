# Project 2 — MD Converter (Mobile App)

Convert anything on your phone to Markdown: shared links, files (pdf/docx/xlsx/pptx/html/csv/ipynb/epub), photos (OCR), YouTube links — with a library of saved conversions.

## Stack (recommended)
- **Flutter (Android-first)** — matches every other dhiva-labs app.
- **Conversion engine: real markitdown running on-device via Chaquopy** (Python-on-Android, integrated in the Android Gradle build; Flutter ↔ Kotlin platform channel ↔ Chaquopy). This gives full-fidelity output identical to desktop/web with zero re-implementation.
- **Fallback/simple path in pure Dart** for instant formats: plain text, csv, html (html→md via Dart `html` parse + own turndown-style walker), so trivial conversions don't need Python startup.
- **Photos/scans: ML Kit text recognition** (proven in Sudoku Solver) → md; EXIF via Dart.
- Optional **"power mode"**: point at project 04's Conversion API for anything the device can't do (e.g. audio transcription) — off by default.
- iOS: out of scope for v1 (no Mac/enrollment); architecture keeps engine behind an interface so an API-backed iOS build is possible later.

## Features

### MVP (Phase 1–4)
1. **Share-sheet target**: share a URL / file / image from any app → lands in converter with format auto-detected (magika-equivalent: extension + mime + content sniff).
2. **File picker + multi-select batch convert**; folder of results in app storage, exportable via SAF ("save to Downloads/Documents") and share-out as .md.
3. **Formats via embedded markitdown**: pdf, docx, xlsx, pptx, epub, ipynb, outlook .msg, html, csv, zip (recursive).
4. **URL converter**: paste/share any URL → fetch → convert (html pages, direct file links). YouTube URL → metadata + transcript (youtube-transcript-api inside Chaquopy).
5. **Image → md**: ML Kit OCR text + EXIF metadata block; document-scan cleanup (crop/deskew via camera flow) in v2.
6. **Library screen**: past conversions, search, preview with rendered markdown (flutter_markdown), copy/share/delete.
7. **Editor**: light md editor with preview toggle for post-conversion touch-ups.

### v2
- Audio → transcript (device speech APIs or power-mode API), camera live document scan, iOS build (API-backed), Obsidian-vault export convention, home-screen quick tile.

## Architecture
```
lib/
  engine/converter.dart        # abstract Converter interface (accepts/convert, mirrors markitdown)
  engine/dart_converters/      # text, csv, html quick paths
  engine/python_engine.dart    # platform channel → Kotlin → Chaquopy markitdown
  engine/mlkit_ocr.dart        # image OCR converter
  engine/api_engine.dart       # optional remote Conversion API
  screens/ (home, convert, library, viewer/editor, settings)
android/app/                   # Chaquopy plugin config, pip: markitdown + chosen extras
```
- Python payload kept lean: install `markitdown[pdf,docx,pptx,xlsx]` + youtube-transcript-api; **exclude magika** (its ML model + onnxruntime are heavy) → patch/bypass stream-guessing with our own extension/mime map (markitdown works fine when StreamInfo has extension+mimetype; verify in Phase 2 spike).
- All conversions run in background isolate/coroutine with progress notifications (foreground service for big batches, pattern from SonicShare).

## Phases
1. **Flutter scaffold + Dart quick converters** — home/convert/library screens, share-sheet + file picker intake, text/csv/html→md, library storage (sqflite index + files).
2. **Chaquopy spike (risk-first)** — minimal Kotlin bridge running `markitdown.convert()` on a docx + pdf on emulator; measure APK size & cold-start; decide magika-bypass patch. **Go/no-go checkpoint: if size/startup unacceptable, pivot engine to power-mode API + expanded Dart converters.**
3. **Full engine integration** — all formats wired through the bridge, batch queue, error surfaces, mime sniffing.
4. **YouTube + URL flow, ML Kit OCR converter.**
5. **Polish** — rendered preview/editor, export/share flows, settings (power-mode endpoint), app icon, release APK.

## Verification
- Dual-path tests: markitdown's own test files (`reference/markitdown/packages/markitdown/tests/test_files/`) pushed to emulator; expected-substring vectors like upstream's `_test_vectors.py`.
- Emulator-verified end-to-end (share-sheet from Chrome/Files app), like previous projects.

## Risks
- **Chaquopy is the big one**: APK size (est. 60–120 MB with pdfminer/openpyxl; pandas is the heaviest — consider xlsx via openpyxl-only custom converter), Python 3.10+ support level, cold start (~1–2 s). Hence Phase 2 spike before committing.
- pdfplumber pulls Pillow (native) — Chaquopy has wheels, but pin versions that exist in its repo.
- Play Store: not a goal for v1 (sideload APK like other projects).
