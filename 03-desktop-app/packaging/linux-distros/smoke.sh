#!/usr/bin/env bash
# Markdrop Studio's own self-test, run in each distribution container by
# in-container.sh (and on the host for the Flatpak, with MARKDROP_CMD and
# MARKDROP_ENGINE set). `markdrop --selftest <file>` starts the app (a GTK
# window on the virtual display), converts one file through the bundled
# md-engine sidecar, prints JSON and exits: it runs the AOT-compiled Dart code
# and the frozen engine together. markitdown's own test documents are
# mounted at /smoke-data by verify.sh.
#
# MARKDROP_ENGINE: where the app must have found its engine. The .rpm and
# Arch packages install it at /opt/markdrop-studio/md-engine/md-engine; the
# AppImage runs from wherever it is extracted, so there only the path below
# the AppImage's root is fixed.
set -euo pipefail
data="${SMOKE_DATA:-/smoke-data}"
cmd="${MARKDROP_CMD:-markdrop}"
engine="${MARKDROP_ENGINE:-/opt/markdrop-studio/md-engine/md-engine}"
if [ -z "${MARKDROP_CMD:-}" ] && [ "${MODE:-}" != appimage ]; then
  # readlink: /usr/bin/markdrop is a symlink to the app, and on Fedora and
  # Arch /usr/sbin (first on root's PATH) is a symlink to /usr/bin.
  test "$(readlink -f "$(command -v markdrop)")" = /opt/markdrop-studio/md_converter_desktop
fi
if [ "${MODE:-}" = appimage ]; then engine="*/opt/markdrop-studio/md-engine/md-engine"; fi

for src in test.docx test.pdf test.pptx test.xlsx; do
  out="/tmp/selftest-$src.json"
  # shellcheck disable=SC2086
  xvfb-run -a -s '-screen 0 1280x800x24' dbus-run-session -- $cmd --selftest "$data/$src" | tee "$out"
  python3 - "$out" "$src" "$engine" <<'PY'
import fnmatch, json, sys
lines = [l for l in open(sys.argv[1]).read().splitlines() if l.startswith("{")]
assert lines, "selftest printed no JSON"
body = json.loads(lines[-1])
assert body["selftest"] and body["ok"], body
assert body["chars"] > 200, body
engine = body["engine"].split()[0]
assert fnmatch.fnmatch(engine, sys.argv[3]), (engine, sys.argv[3])
print(f"{sys.argv[2]}: selftest ok, {body['chars']} chars via {engine}")
PY
done
