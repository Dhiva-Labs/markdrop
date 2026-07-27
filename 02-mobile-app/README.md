# MD Converter Mobile (Android)

Flutter app with the real MarkItDown engine embedded on-device via Chaquopy.

**Status (2026-07-20): FULL APP, emulator-verified.** Share-sheet intake (files/links from any app), file picker (multi-select), URL + YouTube conversion, photo OCR via on-device ML Kit, library of past conversions, and per-result output choice: **Copy text / Share .md / Save file** (MediaStore -> Download/Markdrop/).

Verified on emulator (16 KB page-size image, worst case): docx, pdf, jpg-OCR, html, epub, csv and live Wikipedia URL all convert (headless selftest hook `files/selftest/`); share-intent -> result screen -> Save-file flow screenshot-verified. pptx works only on 4 KB-page devices (most phones today) — python-pptx needs lxml, whose Android wheel is not yet 16 KB-aligned; degrades with a clear message. Plain video files are declined with a hint to use YouTube links (transcripts).

## Spike design
- `app/android/app/build.gradle.kts` — Chaquopy 16.1 with pip `--no-deps` and a hand-picked dependency list: markitdown 0.1.6 **without magika** (magika needs onnxruntime, unavailable on Android) and **without pandas** (xlsx via markitdown is disabled for now to keep the APK small; openpyxl is staged for a custom converter later).
- `app/android/app/src/main/python/magika.py` — stub returning a non-"ok" status so markitdown falls back to extension/mimetype guessing, which the bridge always supplies.
- `app/android/app/src/main/python/convert.py` — `convert_file(path) -> JSON`, `engine_info()`.
- `MainActivity.kt` — `md_engine` MethodChannel, Python calls on a background thread.
- `lib/main.dart` — spike UI: engine diagnostics (Python version, module availability, cold-start ms) + "convert sample HTML" button.

## Toolchain gotchas (hard-won)
- Chaquopy is **incompatible with Gradle 9 / AGP 9** — downgraded to Gradle 8.10.2 + AGP 8.7.3 + Kotlin 2.1.0 in `android/`.
- Chaquopy can't find AGP (or itself) through Flutter's plugin-loader — both artifacts must be on the **root buildscript classpath** (`android/build.gradle.kts`).
- Must pin `chaquopy { defaultConfig { version = "3.12" } }` or pip resolves against an ancient Python and only finds markitdown 0.0.1a1.
- Flutter pre-seeds `armeabi-v7a` in ndk.abiFilters — `abiFilters.clear()` before adding arm64-v8a/x86_64 (no Python 3.12 build for v7a).
- Native wheels must exist in chaquo.com/pypi-13.1 for cp312: cryptography==42.0.8, Pillow==11.0.0, lxml==5.3.0.
- Global pip `--no-deps` also skips Chaquopy's native support wheels — list explicitly: chaquopy-libxml2/libxslt (lxml), chaquopy-libjpeg/libpng (Pillow), cffi + pycparser (cryptography).
- **Chaquopy 17.0.0 required** for 16 KB page-size devices (16.x wheels dlopen-fail with "program alignment (4096) cannot be smaller than system page size (16384)").
- Chaquopy needs a local `buildPython` **with pip**; uv venvs need `--seed` (`.buildpython/`).
- minSdk forced to ≥ 24; JAVA_HOME for direct gradlew runs: `/snap/android-studio/232/jbr`.

## Build
```bash
cd app && flutter build apk --debug
```

## After go/no-go
Full app per PLAN.md: share-sheet intake, batch queue, library with rendered preview, ML Kit OCR for photos, YouTube URL flow, optional power-mode API.
