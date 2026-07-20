# Project 1 — MD Clipper (Browser Extension)

Convert the current webpage — or a selected part of it, an image, a video, or a pasted link (YouTube etc.) — to Markdown, from the browser toolbar.

## Stack
- **Manifest V3**, TypeScript, Vite build. Targets: Chrome/Edge/Brave + Firefox (MV3 with `browser_specific_settings`).
- Client-side conversion: **@mozilla/readability** (article extraction) + **Turndown** (+ turndown-plugin-gfm for tables/strikethrough/task-lists).
- Heavy formats (PDF link, docx link, YouTube transcript): call the **Conversion API** from project 04 (configurable endpoint in options, default off → those features greyed out until an endpoint is set).
- No frameworks for UI (plain TS + HTML/CSS popup); keeps review/size small.

## Features

### MVP (Phase 1–3)
1. **Whole-page → Markdown**: Readability article mode OR "full page" mode (whole body through Turndown). Output includes front-matter (url, title, saved date).
2. **Element picker** ("select what to convert"): content-script overlay — hover highlights DOM blocks (like devtools inspector), click to select, shift-click to add multiple blocks, Esc to cancel → converts only that subtree. Also: if user has a native text selection, "Convert selection" uses it.
3. **Image → Markdown**: right-click an image → context-menu "Copy as Markdown" (`![alt](src)` + optional download of image alongside .md); page images inside converted content keep absolute URLs.
4. **YouTube**: 
   - On a YouTube watch page: one click → title/channel/description + transcript → md.
   - **Inside popup: a link box** — paste any YouTube URL → converted to md without visiting the page. Transcript fetch: try client-side InnerTube/timedtext endpoints first; fall back to Conversion API (`youtube-transcript-api`) when configured.
5. **Output actions**: preview pane in popup, Copy to clipboard, Download `.md` (filename from title), remember last mode.
6. **Context menus**: "Convert page", "Convert selection", "Convert link target" (sends URL to API for pdf/docx/etc.), "Copy image as Markdown".

### Phase 4+ (v2)
- Batch: convert all open tabs in window.
- Clip-to-folder: File System Access API to save into a chosen notes folder.
- Site rules (per-domain default mode), dark-mode popup, keyboard shortcuts.
- Firefox listing on AMO, Chrome Web Store packaging.

## Architecture
```
src/
  background.ts        # service worker: context menus, downloads, API calls
  content/picker.ts    # element-picker overlay + DOM capture
  content/extract.ts   # Readability + Turndown pipeline (runs in page ctx)
  popup/               # popup UI: mode buttons, YouTube link box, preview
  options/             # API endpoint, filename template, front-matter toggle
  lib/markdown.ts      # shared md conventions (front-matter, sanitising)
  lib/youtube.ts       # transcript fetch client-side + API fallback
manifest.chrome.json / manifest.firefox.json (generated from one source)
```
- Turndown config mirrors markitdown's `_CustomMarkdownify` decisions: ATX headings, strip `javascript:` links, drop `data:` URI images (truncate), checkbox inputs → `[x]`/`[ ]`.
- Permissions: `activeTab`, `scripting`, `contextMenus`, `downloads`, `storage`; optional host permission only for the user-configured API origin. No broad `<all_urls>` at install time (use activeTab).

## Phases
1. **Scaffold + page conversion** — Vite MV3 scaffold, Readability+Turndown pipeline, popup with Copy/Download, front-matter. Verify on 5 varied sites (blog, docs, news, SPA, table-heavy).
2. **Element picker** — overlay, multi-select, selection→md. Verify picker on nested layouts.
3. **YouTube + link box** — watch-page button, popup URL field, transcript client-side path; context-menu "Convert link target" wired to API stub.
4. **API integration + options** — endpoint config, pdf/docx link conversion via project 04, error surfaces.
5. **Firefox port + packaging** — manifest split, web-ext build, store zips in `dist/`.

## Verification
- Load unpacked in Chromium via `chrome://extensions`; drive with the in-app browser where possible; test matrix doc in `test/PAGES.md` (list of URLs + expected md snippets).
- Unit-test the md pipeline in Node (jsdom + fixture HTML → expected md), markitdown-style "test vectors".

## Risks / notes
- YouTube transcript endpoints are unofficial and break periodically → API fallback is the safety net; degrade to metadata-only md if both fail.
- MV3 service-worker lifetime: keep conversions in content script/popup, background only orchestrates.
- Some sites' CSP block content-script injected iframes — picker uses plain absolutely-positioned divs, no iframes.
