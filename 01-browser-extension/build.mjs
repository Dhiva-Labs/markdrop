// esbuild bundler: builds dist/ (Chrome MV3) and dist-firefox/ (Firefox MV3
// event page + gecko id), then store-ready zips in dist-zips/.

import { build } from "esbuild";
import { cpSync, mkdirSync, rmSync, readFileSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";

const targets = [
  { dir: "dist", firefox: false },
  { dir: "dist-firefox", firefox: true },
];

const common = { bundle: true, minify: true, logLevel: "silent", target: "chrome110" };

for (const { dir, firefox } of targets) {
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(`${dir}/popup`, { recursive: true });
  mkdirSync(`${dir}/options`, { recursive: true });
  mkdirSync(`${dir}/content`, { recursive: true });

  // Background as classic IIFE so the same file works as a Chrome service
  // worker and a Firefox event-page script.
  await build({ ...common, entryPoints: ["src/background.js"], outfile: `${dir}/background.js`, format: "iife" });
  await build({ ...common, entryPoints: ["src/content/extract.js"], outfile: `${dir}/content/extract.js`, format: "iife" });
  await build({ ...common, entryPoints: ["src/content/picker.js"], outfile: `${dir}/content/picker.js`, format: "iife" });
  await build({ ...common, entryPoints: ["src/popup/popup.js"], outfile: `${dir}/popup/popup.js`, format: "iife" });
  await build({ ...common, entryPoints: ["src/options/options.js"], outfile: `${dir}/options/options.js`, format: "iife" });

  const manifest = JSON.parse(readFileSync("manifest.json", "utf8"));
  if (firefox) {
    manifest.background = { scripts: ["background.js"] };
    manifest.browser_specific_settings = {
      gecko: { id: "md-clipper@dhiva-labs", strict_min_version: "128.0" },
    };
  }
  writeFileSync(`${dir}/manifest.json`, JSON.stringify(manifest, null, 2));
  cpSync("src/popup/popup.html", `${dir}/popup/popup.html`);
  cpSync("src/options/options.html", `${dir}/options/options.html`);
  mkdirSync(`${dir}/icons`, { recursive: true });
  for (const size of [16, 32, 48, 128]) {
    cpSync(`icons/icon${size}.png`, `${dir}/icons/icon${size}.png`);
  }
}

// Store zips
rmSync("dist-zips", { recursive: true, force: true });
mkdirSync("dist-zips");
const version = JSON.parse(readFileSync("manifest.json", "utf8")).version;
execSync(`cd dist && zip -qr ../dist-zips/md-clipper-chrome-${version}.zip .`);
execSync(`cd dist-firefox && zip -qr ../dist-zips/md-clipper-firefox-${version}.zip .`);

console.log(`Built dist/ (Chrome), dist-firefox/ (Firefox), dist-zips/*-${version}.zip`);
