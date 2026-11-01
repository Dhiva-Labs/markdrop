#!/usr/bin/env bash
# Installs the Flatpak bundle on the CI host and runs it there, the way a
# user would get it: the GNOME runtime comes from Flathub.
#
# usage: sudo test-bundle.sh <bundle.flatpak> <test documents dir>
#
#   1. every ELF file under /app finds all of its libraries inside the
#      sandbox (ldd, run through `flatpak run --command`)
#   2. the app's --selftest converts the four test documents through the
#      bundled engine inside the sandbox (../linux-distros/smoke.sh)
#   3. the window stays up for 20 s under Xvfb
#
# Runs as root: Ubuntu 24.04 restricts unprivileged user namespaces, which
# bubblewrap needs as a normal user.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ $# -eq 2 ] || { echo "usage: $0 <bundle.flatpak> <test documents dir>" >&2; exit 2; }
bundle="$(readlink -f "$1")"
data="$(cd "$2" && pwd)"
app=com.dhivalabs.MarkdropStudio
export XDG_RUNTIME_DIR=/run/user/0
mkdir -p -m 0700 "$XDG_RUNTIME_DIR"

flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install -y --noninteractive "$bundle"
flatpak info "$app"

echo "::group::ldd inside the sandbox"
flatpak run --command=bash "$app" -euo pipefail -c '
  mapfile -t elfs < <(find /app -type f | while IFS= read -r f; do
    [ "$(head -c 4 "$f" | od -An -tx1 | tr -d " \n")" = 7f454c46 ] && echo "$f"
  done)
  libdirs="$(for f in "${elfs[@]}"; do case "$f" in *.so|*.so.*) dirname "$f" ;; esac; done | sort -u | paste -sd:)"
  missing=0
  for f in "${elfs[@]}"; do
    if LD_LIBRARY_PATH="$libdirs" ldd "$f" 2>&1 | grep "not found" > /dev/null; then
      echo "missing libraries for $f:"
      LD_LIBRARY_PATH="$libdirs" ldd "$f" | grep "not found"
      missing=1
    fi
  done
  echo "${#elfs[@]} ELF files checked with ldd"
  [ "$missing" = 0 ]
'
echo "::endgroup::"

echo "::group::self-test inside the sandbox"
MARKDROP_CMD="flatpak run --filesystem=$data:ro $app" \
  MARKDROP_ENGINE=/app/lib/markdrop-studio/md-engine/md-engine \
  SMOKE_DATA="$data" bash "$here/../linux-distros/smoke.sh"
echo "::endgroup::"

echo "::group::window stays up"
cat > /tmp/flatpak-gui.sh <<EOS
flatpak run $app > /tmp/flatpak-gui.log 2>&1 &
pid=\$!
for _ in \$(seq 1 20); do kill -0 "\$pid" 2> /dev/null || break; sleep 1; done
if kill -0 "\$pid" 2> /dev/null; then ok=1; echo "still running after 20s"; else ok=0; echo "exited early"; fi
flatpak kill $app || kill "\$pid"
cat /tmp/flatpak-gui.log
if grep -E 'error while loading shared libraries|cannot open shared object|undefined symbol' /tmp/flatpak-gui.log; then ok=0; fi
[ "\$ok" = 1 ]
EOS
xvfb-run -a -s '-screen 0 1280x800x24' dbus-run-session -- bash /tmp/flatpak-gui.sh
echo "::endgroup::"
echo "Flatpak bundle OK"
