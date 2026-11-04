# Building Markdrop Clipper for Firefox

The extension's JavaScript is bundled and minified with esbuild. To reproduce
the uploaded package from this source:

Tested with Ubuntu 26.04, Node.js 24.13.0 and npm 11.6.2.

The source archive keeps the repository layout: the repository's `LICENSE` at
the top and the extension in `01-browser-extension/`. The build copies that
`LICENSE` into the package, so run it from the extension folder:

    cd 01-browser-extension
    npm ci
    node build.mjs

The Firefox package is written to `dist-firefox/` (zipped as
`dist-zips/md-clipper-firefox-<version>.zip`). Entry points live in `src/`.
Third-party code comes from npm (exact versions pinned in package-lock.json):
@mozilla/readability, turndown and turndown-plugin-gfm. Their licence texts
are listed in `THIRD_PARTY_NOTICES.md` and ship in the package's `licenses/`.
