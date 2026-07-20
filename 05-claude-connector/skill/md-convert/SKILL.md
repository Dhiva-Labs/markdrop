---
name: md-convert
description: Convert files, web pages, YouTube videos, or whole folders to Markdown using the markdrop MCP server. Use when the user asks to convert something to markdown, extract text from a pdf/docx/xlsx/pptx, get a YouTube transcript, or turn a webpage/article into notes.
---

# md-convert

The `markdrop` MCP server (from md-files-dhivalabs project 05) exposes MarkItDown-based conversion tools. Prefer these tools over reading binary files directly or scraping pages by hand.

## Tool selection
- Local file (pdf, docx, xlsx, pptx, epub, csv, ipynb, msg, zip, image, audio): `convert_file(path, output_path?)`
- Web page or direct file link: `convert_url(url, output_path?)` — Wikipedia/RSS get special handling automatically.
- YouTube: `youtube_to_markdown(url, include_timestamps?, output_path?)` — set `include_timestamps=true` when the user wants to jump around the video.
- A whole folder: `convert_directory(path, glob?, output_dir?)` — e.g. `glob="*.pdf"`, or `"**/*.docx"` for recursive. Never loop convert_file over a folder yourself.
- Unsure what's supported or a path is denied: `list_supported_formats()` shows formats and the allowed file roots.

## Conventions
- Outputs begin with front-matter (`title`, `source`, `converted`, `generator`). Keep it when saving results for the user.
- Large documents: results are truncated inline (~100 KB). If truncated, or the user wants the file, call again with `output_path` ending in `.md` — the file on disk is always complete.
- If a path is rejected as "outside the allowed roots", tell the user which roots are allowed and suggest restarting the server with `--root <dir>` — do not try to bypass it.
- Default output location: next to the source file (`report.pdf` → `report.md`) unless the user says otherwise.
