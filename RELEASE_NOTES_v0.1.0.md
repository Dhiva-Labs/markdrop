# Markdrop v0.1.0 — first release 🎉

> **Turn anything into Markdown.** Web pages, PDFs, Office documents, YouTube videos, whole folders — one suite, six ways to convert. From **Dhiva Labs**, powered by Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) engine.

This is the initial release of the entire Markdrop suite — six products sharing one conversion engine and one output convention (clean GFM markdown with `title` / `source` / `converted` front-matter).

## The suite

| Product | What it does | Status |
|---|---|---|
| 🧩 **Markdrop Clipper** | Browser extension: article/full-page/selection conversion, an element picker, right-click menus, and YouTube-link → transcript with `[hh:mm:ss]` timestamps | Chrome + Firefox packages, submitted to Chrome Web Store |
| 🖥️ **Markdrop Studio** | Desktop app: drag-and-drop batch conversion (pdf, docx, xlsx, pptx, epub, html, URLs, YouTube) with rendered preview — engine bundled, works offline | Linux .deb |
| 📱 **Markdrop Mobile** | Android app running the *real* MarkItDown engine fully on-device (no server, no upload) | Engine-verified debug APK; full UI in development |
| 🌐 **Markdrop Web** | Self-hostable web converter + REST API (upload / URL / YouTube endpoints, SSRF-guarded, rate-limited) — also the backend for the bot | Run from source or Docker |
| 🤖 **markdrop-mcp** | MCP connector that gives Claude six conversion tools (`convert_file`, `convert_directory`, `youtube_to_markdown`, …) with path-allowlist security | pip wheel |
| ✈️ **Markdrop Bot** | Telegram bot: send any document, link, photo or YouTube URL — get a `.md` file back | Run from source (needs your bot token) |

## Downloads (this release)

| Asset | Install |
|---|---|
| `markdrop-clipper-chrome-0.1.0.zip` | `chrome://extensions` → Developer mode → Load unpacked (or wait for the Web Store listing) |
| `markdrop-clipper-firefox-0.1.0.zip` | `about:debugging` → This Firefox → Load Temporary Add-on |
| `markdrop-studio_0.1.0_amd64.deb` | `sudo dpkg -i markdrop-studio_0.1.0_amd64.deb` → launch **Markdrop Studio** or run `markdrop` |
| `markdrop-mobile-0.1.0-debug.apk` | `adb install markdrop-mobile-0.1.0-debug.apk` (arm64/x86_64, Android 7+) |
| `markdrop_mcp-0.1.0-py3-none-any.whl` | `pip install markdrop_mcp-0.1.0-py3-none-any.whl` then `claude mcp add markdrop -- markdrop-mcp --root ~/Documents` |

<details>
<summary>SHA-256 checksums</summary>

```
61d4ed800a472989244cd2e9fac7e4b60626923bbb47693c02aabb2fec1acfba  markdrop-clipper-chrome-0.1.0.zip
2477386ba9e5788b955b3534d594be160a64768e51b7a78a7a19cef14827896d  markdrop-clipper-firefox-0.1.0.zip
37f6a290271d18d099d9dcf15585b8876e6b0bb7e02736cee733fc6cebd76b0e  markdrop_mcp-0.1.0-py3-none-any.whl
60f518e69e63f7bc3664d7a16befd87ef3d5de132c3f32ac018e7e8959635d02  markdrop-mobile-0.1.0-debug.apk
be7c272db4c9faf834e7f24f2ad7a690161636a7e66d3f24026b7227a1fde703  markdrop-studio_0.1.0_amd64.deb
```
</details>

## Highlights

- **Consistent output everywhere** — every product emits the same markdown conventions (ATX headings, GFM tables, task-list checkboxes, stripped `javascript:` links) and front-matter stamped with `generator: dhiva-labs/markdrop-<product>`.
- **Privacy-first** — the extension converts entirely in your browser; the mobile app converts entirely on your phone; the web API and bot are self-hosted. Nothing is sent to third parties.
- **Element picker** (Clipper) — hover-highlight any block on a page, shift-click to add more, convert exactly what you selected.
- **YouTube transcripts** — from the extension popup, the desktop app, the web UI, the bot, or Claude — with optional timestamps.
- **Claude integration** — `markdrop-mcp` exposes conversion as MCP tools with canonical-path allowlisting (symlink-escape tested), SSRF-guarded URL fetching, and output capping so big documents don't flood the context.
- **Real engine on Android** — MarkItDown + Python 3.12 embedded via Chaquopy 17: ~0.8 s cold start, HTML→md in ~540 ms on-device, including on Android's new 16 KB page-size builds.

## Verified

- 51 automated tests across the suite (extension pipeline, web API over MarkItDown's own test corpus, MCP stdio round-trip, engine golden tests, bot handlers) — all passing.
- End-to-end checks: live Wikipedia + YouTube conversions, desktop headless self-test through the bundled engine, Android emulator conversion (screenshot-verified).

## Known limitations (v0.1.0)

- **Mobile APK is a debug engine-spike build** — it proves the on-device engine; the full app (share-sheet intake, batch queue, library, OCR) is next. xlsx and audio transcription are not yet enabled on mobile.
- **Markdrop Studio** ships for Linux/amd64 only; Windows/macOS builds are planned via CI. Watch-folders and clipboard watcher are on the roadmap.
- **Firefox package** is built but not yet submitted to AMO.
- YouTube transcript extraction relies on public caption endpoints and may need updates if YouTube changes its page structure.
- LLM-powered extras (image descriptions, OCR) are off by default and require your own API key.

## What's next

Full mobile app UI → Firefox/AMO listing → Studio watch-folders + Windows/macOS builds → web batch-to-zip + suite landing page → Docker images for Web + Bot.

---
*Markdrop is an independent project from Dhiva Labs, built on the MIT-licensed MarkItDown engine. Licensed MIT.*
