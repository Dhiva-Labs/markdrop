# MD Clipper — Browser Extension

Convert web pages, selections, picked elements, images and YouTube videos to Markdown, right from the toolbar. Manifest V3, no frameworks; Readability + Turndown configured to match the suite's markitdown conventions.

## Build & load
```bash
npm install
npm run build        # -> dist/
npm test             # 12 pipeline tests (node --test + jsdom)
```
Then Chrome/Edge/Brave → `chrome://extensions` → enable **Developer mode** → **Load unpacked** → pick the `dist/` folder.

## Features
- **Popup**: Article mode (Readability), Full page, Selection, and **Pick element** (hover-highlight overlay; shift-click to add blocks, Enter converts, Esc cancels; in-page Copy/Download toolbar).
- **YouTube box in the popup**: paste any watch/shorts/youtu.be link → title, channel, description + transcript (optional `[hh:mm:ss]` timestamps) without opening the page. Auto-prefills when you're on a YouTube tab.
- **Context menus**: Convert page / Convert selection / Select element / Copy image as Markdown.
- **Keyboard**: `Alt+Shift+M` converts the current page (article mode) straight to a download.
- **Options**: front-matter toggle, keep-data-URIs, Conversion API endpoint + key (for the upcoming linked-PDF/Office conversion via project 04).
- Output uses the suite's front-matter (`title`/`source`/`converted`/`generator`) and markitdown-style markdown (ATX headings, GFM tables, no `javascript:` links, truncated `data:` URIs, `[x]` checkboxes).

## Structure
```
src/background.js       # context menus, downloads, keyboard command
src/content/extract.js  # Readability+Turndown, answers md-extract messages
src/content/picker.js   # element picker overlay + in-page result toolbar
src/popup/  src/options/
src/lib/markdown.js     # shared Turndown config + front-matter (unit-tested)
src/lib/youtube.js      # watch-page parsing + json3 transcript (unit-tested)
build.mjs               # esbuild -> dist/
```

## Known limits (v0.1)
- YouTube transcript uses the page's caption tracks (unofficial); if YouTube changes its layout, the parser falls back to a clear error. Metadata still converts.
- "Convert link target" (send a linked .pdf/.docx to the project-04 API) is wired in options but lands in the next iteration.
- Firefox port pending (manifest tweaks + `browser_specific_settings`).
