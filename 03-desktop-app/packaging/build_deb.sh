#!/usr/bin/env bash
# Build markdrop-studio_<version>_<arch>.deb from a finished release build.
#
#   packaging/build_deb.sh [OUT_DIR] [VERSION]
#
# Inputs (build them first, on a machine of the architecture you want):
#   app/build/linux/<x64|arm64>/release/bundle   flutter build linux --release
#   engine/dist/md-engine                        the PyInstaller one-folder build
#
# The architecture comes from dpkg, never from a constant, so the same script
# produces the amd64 and the arm64 package. VERSION defaults to the contents of
# packaging/deb-version. Layout (unchanged since 0.1.1):
#   /opt/markdrop-studio/{md_converter_desktop,lib,data,md-engine,icon.png}
#   /usr/bin/markdrop -> /opt/markdrop-studio/md_converter_desktop
#   /usr/share/applications/markdrop-studio.desktop
#   /usr/share/icons/hicolor/256x256/apps/markdrop-studio.png
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

OUT_DIR="${1:-$ROOT/dist}"
VERSION="${2:-$(tr -d '[:space:]' < "$HERE/deb-version")}"

DEB_ARCH="$(dpkg --print-architecture)"
case "$DEB_ARCH" in
  amd64) FLUTTER_ARCH=x64 ;;
  arm64) FLUTTER_ARCH=arm64 ;;
  *)
    echo "error: unsupported architecture '$DEB_ARCH' (amd64 or arm64)" >&2
    exit 1
    ;;
esac

BUNDLE="$ROOT/app/build/linux/$FLUTTER_ARCH/release/bundle"
ENGINE="$ROOT/engine/dist/md-engine"
for need in "$BUNDLE/md_converter_desktop" "$ENGINE/md-engine" "$ROOT/icon.png"; do
  [ -e "$need" ] || { echo "error: $need not found" >&2; exit 1; }
done

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
PKG="$STAGE/pkg"
APP="$PKG/opt/markdrop-studio"

mkdir -p "$APP" "$PKG/usr/bin" "$PKG/usr/share/applications" \
  "$PKG/usr/share/icons/hicolor/256x256/apps" "$PKG/DEBIAN"

cp -a "$BUNDLE/." "$APP/"
cp -a "$ENGINE" "$APP/md-engine"
install -m 0644 "$ROOT/icon.png" "$APP/icon.png"
install -m 0644 "$ROOT/icon.png" \
  "$PKG/usr/share/icons/hicolor/256x256/apps/markdrop-studio.png"
ln -s /opt/markdrop-studio/md_converter_desktop "$PKG/usr/bin/markdrop"

cat > "$PKG/usr/share/applications/markdrop-studio.desktop" <<DESKTOP
[Desktop Entry]
Name=Markdrop Studio
Comment=Convert anything to Markdown - from Dhiva Labs
Exec=/opt/markdrop-studio/md_converter_desktop
Icon=markdrop-studio
Terminal=false
Type=Application
Categories=Utility;Office;
DESKTOP

# Normalise modes: directories 755, plain files 644, keep executables.
find "$PKG" -type d -exec chmod 0755 {} +
find "$PKG/opt" "$PKG/usr/share" -type f ! -perm /111 -exec chmod 0644 {} +
chmod 0755 "$PKG/DEBIAN"

SIZE_KB="$(du -sk --exclude=DEBIAN "$PKG" | cut -f1)"
cat > "$PKG/DEBIAN/control" <<CONTROL
Package: markdrop-studio
Version: $VERSION
Section: utils
Priority: optional
Architecture: $DEB_ARCH
Maintainer: Dhiva Labs <dhivakar1010@gmail.com>
Installed-Size: $SIZE_KB
Depends: libgtk-3-0t64 | libgtk-3-0
Description: Markdrop Studio - convert anything to Markdown (from Dhiva Labs)
 Drag-and-drop batch converter for pdf, docx, xlsx, pptx, epub, html,
 URLs and YouTube links, with rendered Markdown preview.
CONTROL

mkdir -p "$OUT_DIR"
DEB="$OUT_DIR/markdrop-studio_${VERSION}_${DEB_ARCH}.deb"
dpkg-deb --root-owner-group -Zxz --build "$PKG" "$DEB" > /dev/null
echo "$DEB"
