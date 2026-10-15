# Changelog

The repository holds several products that are versioned on their own: the browser extension
(Clipper), the mobile app, the desktop app (Studio), the web app, markdrop-mcp and the bot. A
tagged release (`vX.Y.Z`) is the suite release; the component files it carries keep their own
version in the file name.

## v0.1.1 - 2026-10-16

### Added
- Markdrop Studio for Linux arm64: `markdrop-studio_0.1.2_arm64.deb`, built and tested on a
  native arm64 runner (engine golden tests, frozen engine conversions, app self-test of the
  installed package), next to the amd64 package.
- `03-desktop-app/packaging/build_deb.sh`: one packaging script for the amd64 and arm64 .deb
  (the architecture comes from `dpkg --print-architecture`).
- CI workflow `studio-linux.yml`: builds Studio for x64 and arm64 on every change to
  `03-desktop-app/`, and attaches the .debs to a published release without replacing files that
  are already on it.

### Changed
- Studio .deb version is now `0.1.2` (`03-desktop-app/packaging/deb-version`). The amd64
  package shipped with v0.1.0 was `0.1.1`; the rebuilt packages get a new version so the two
  never share a version and a file name.
- The Studio .deb is no longer amd64-only; the README documents both packages.

### Unchanged in this release
- Clipper (Chrome and Firefox) 0.1.0, Mobile 0.1.0 APK, markdrop-mcp 0.1.0, Web and Bot: same
  code and the same files as v0.1.0.

## v0.1.0 - 2026-07-20

First release of the suite: Clipper, Studio (Linux amd64 .deb), Mobile (Android APK), Web,
markdrop-mcp and the Telegram bot.
