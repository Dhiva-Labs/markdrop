# Markdrop (md-files-dhivalabs) — from Dhiva Labs

[![ARM64 builds](https://github.com/Dhiva-Labs/markdrop/actions/workflows/studio-linux.yml/badge.svg?branch=main)](https://github.com/Dhiva-Labs/markdrop/actions/workflows/studio-linux.yml)
![Markdrop Studio: Linux x64 | arm64](https://img.shields.io/badge/Studio-Linux%20x64%20%7C%20arm64-informational?logo=linux&logoColor=white)
![Linux: deb | rpm | Arch | AppImage | Flatpak](https://img.shields.io/badge/Linux-deb%20%7C%20rpm%20%7C%20Arch%20%7C%20AppImage%20%7C%20Flatpak-informational?logo=linux&logoColor=white)

**Markdrop** is the suite brand: Markdrop Clipper (extension), Markdrop (mobile), Markdrop Studio (desktop), Markdrop Web + API, markdrop-mcp (Claude connector), Markdrop Bot (Telegram). All products carry "from Dhiva Labs" attribution and emit front-matter generator strings `dhiva-labs/markdrop-<product>`.

Multi-plan project built around Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) (file → Markdown conversion engine).

## Install Markdrop Studio (Linux desktop)

Markdrop Studio is released as a `.deb` for both Linux architectures. Take the one that matches
`dpkg --print-architecture`:

| Machine | Asset |
|---|---|
| x86-64 (`amd64`) | `markdrop-studio_<version>_amd64.deb` |
| 64-bit ARM (`arm64`) | `markdrop-studio_<version>_arm64.deb` |

```bash
sudo apt install ./markdrop-studio_<version>_arm64.deb   # or ..._amd64.deb
markdrop                                                   # or launch "Markdrop Studio" from the app menu
```

The package bundles the Flutter app and the frozen conversion engine (Python 3.12 and markitdown),
so nothing else needs installing except GTK 3. CI builds both packages on native runners
(`.github/workflows/studio-linux.yml`), runs the engine's golden tests and the app's
`--selftest` on each architecture, and attaches them to published releases. They are built on
Ubuntu 24.04, so they need that release's C library or newer.

### Other Linux distributions

From the next release on, the same build is also attached as packages for other distributions
(x86-64 file names shown; the arm64 files end in `aarch64`):

| Distribution | Asset | Install |
|---|---|---|
| Fedora, RHEL/Rocky/Alma | `markdrop-studio-<version>-1.x86_64.rpm` | `sudo dnf install ./markdrop-studio-<version>-1.x86_64.rpm` |
| openSUSE Tumbleweed | the same `.rpm` | `sudo zypper install --allow-unsigned-rpm ./markdrop-studio-<version>-1.x86_64.rpm` |
| Arch, Manjaro, EndeavourOS | `markdrop-studio-<version>-1-x86_64.pkg.tar.zst` | `sudo pacman -U ./markdrop-studio-<version>-1-x86_64.pkg.tar.zst` |
| AUR | `markdrop-studio-bin-<version>-aur.tar.gz` (PKGBUILD + .SRCINFO) | `markdrop-studio-bin` in the AUR once published |
| any glibc distribution | `MarkdropStudio-<version>-x86_64.AppImage` | `chmod +x MarkdropStudio-<version>-x86_64.AppImage && ./MarkdropStudio-<version>-x86_64.AppImage` |
| any distribution with Flatpak | `markdrop-studio-<version>-x86_64.flatpak` | `flatpak install --user ./markdrop-studio-<version>-x86_64.flatpak` (the GNOME runtime comes from Flathub) |

All of them repackage the `.deb`'s files, so they behave the same. Built on Ubuntu 24.04, the
`.rpm`, Arch package and AppImage need glibc 2.38 or newer and GTK 3 (Fedora 39+, openSUSE
Tumbleweed, current Arch; not RHEL 9 or openSUSE Leap 15); the Flatpak brings its own runtime.
The `.rpm` is unsigned, hence zypper's `--allow-unsigned-rpm`. The Flatpak can read your home
directory (dropped files arrive as plain paths) and saves through the file chooser portal; see
`03-desktop-app/packaging/flatpak/README.md`. CI installs each package on Fedora, openSUSE
Tumbleweed and Arch Linux (the AppImage on Fedora, the Flatpak on Ubuntu with the Flathub
runtime) on both architectures and runs the app's `--selftest` there; Arch Linux has no official
arm64 image, so the arm64 Arch package gets a static check only.

## Layout
- `MASTER_PLAN.md` — suite overview, shared architecture, build order, open questions.
- `01-browser-extension/` — MD Clipper (MV3, TS): page/selection/image/YouTube → md.
- `02-mobile-app/` — Flutter Android converter (Chaquopy-embedded markitdown).
- `03-desktop-app/` — Flutter desktop (Linux/Win/Mac) + PyInstaller markitdown sidecar.
- `04-web-app/` — FastAPI + static frontend; doubles as the suite's shared Conversion API.
- `05-claude-connector/` — MCP server (stdio + HTTP) + Claude Code skill.
- `notes/markitdown-analysis.md` — full architecture/code analysis of MarkItDown. Read this instead of re-reading the source.
- `reference/markitdown/` — full source snapshot of the upstream repo (no .git), for lookup only.

## Status
- 2026-07-20: upstream analyzed; PLAN.md written for all five projects; plans approved.
- 2026-07-20: **04-web-app Phases 1–3 done and verified** — API (file/url/youtube + SSRF guard, rate limit, API key, process-pool timeouts), frontend (upload/URL/YouTube tabs, preview, copy/download), Dockerfile. 14 tests pass; browser-verified live. Remaining: batch-to-zip, suite landing page.
- 2026-07-20: **05-claude-connector done and verified** — md-suite-mcp server (6 tools, roots allowlist w/ symlink protection, output capping, stdio + HTTP with bearer token), Claude Code skill, config snippets. 11 tests pass incl. real stdio MCP round-trip; URL + timestamped YouTube live-verified.
- 2026-07-20: Project #6 chosen: **Telegram bot** (plan written). md-suite MCP connector registered user-scope in ~/.claude.json and verified live in-session.
- 2026-07-20: **01-browser-extension FINISHED** — added API link-target conversion, Firefox MV3 target (event page + gecko id), store zips in dist-zips/ (chrome + firefox). 12 tests pass.
- 2026-07-20: **03-desktop-app .deb built** — dist/md-converter_0.1.0_amd64.deb (88 MB, engine bundled at /opt/md-converter/md-engine, /usr/bin/md-converter symlink, .desktop entry); packaged tree selftest-verified against bundled engine.
- 2026-07-20: **02-mobile-app spike: GO ✅** — real markitdown embedded via Chaquopy 17, emulator-verified (Python 3.12.12 cold start 0.8 s, HTML→md in 541 ms, correct front-matter/tables on a 16 KB page-size image). Toolchain recipe + 11 gotchas in 02-mobile-app/README.md. Next: full app screens.
- 2026-07-20: **06-telegram-bot built** — python-telegram-bot v21 thin client over the 04 API (documents/photos/URLs/YouTube, allowlist, /formats, 20 MB cap). 10 tests pass incl. live API round-trip. Needs MD_BOT_TOKEN from @BotFather for a real Telegram run.
- 2026-07-20: **03-desktop-app Phases 1–2 done** — md-engine sidecar (JSON one-shot + warm stdio serve; 4 golden tests) frozen with PyInstaller (181 MB, works standalone); Flutter Linux app (dropzone, URL box, batch queue, rendered/raw preview, copy/save) built release + verified via headless `--selftest` (docx through real sidecar) + clean 10 s GUI launch. Remaining: watch folders, packaging, Win/mac CI.
- 2026-07-20: **01-browser-extension Phases 1–3 done** — MD Clipper MV3 (article/full/selection modes, element picker with in-page toolbar, YouTube popup box with timestamped transcripts, context menus, keyboard shortcut, options). 12 node tests pass; dist/ built via esbuild; all bundles parse. Load via chrome://extensions → Load unpacked → dist/. Remaining: API-linked file conversion, Firefox port, store packaging.

## Sponsors

Dhiva Labs is an independent, self-funded lab. [Sponsorships](https://github.com/sponsors/Dhiva-Labs) help bring this project and the rest of Dhiva Labs to every platform, iPhone and Mac included.

[![Sponsor Dhiva Labs](https://img.shields.io/badge/Sponsor-Dhiva%20Labs-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Dhiva-Labs)

Monthly sponsors at $10 and up are listed here:

<!-- sponsors -->
*Be the first: [sponsor Dhiva Labs](https://github.com/sponsors/Dhiva-Labs).*
<!-- sponsors -->
