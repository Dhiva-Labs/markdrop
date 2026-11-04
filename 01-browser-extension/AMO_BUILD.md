# Building Markdrop Clipper for Firefox

The extension's JavaScript is bundled and minified with esbuild. To reproduce
the uploaded package from this source:

Tested with Ubuntu 26.04, Node.js 24.13.0 and npm 11.6.2.

    npm ci
    node build.mjs

The Firefox package is written to `dist-firefox/` (zipped as
`dist-zips/md-clipper-firefox-<version>.zip`). Entry points live in `src/`.
Third-party code comes from npm (exact versions pinned in package-lock.json):
@mozilla/readability, turndown and turndown-plugin-gfm.
