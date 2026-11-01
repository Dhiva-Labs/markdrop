#!/usr/bin/env bash
# Renders the AUR PKGBUILD for one release and proves it builds.
#
# usage: aur.sh <amd64.deb> <arm64.deb> <outdir>
#
# Fills PKGBUILD.in with the version, the release download URL and the
# sha256 of both .debs and of the license, then, in an archlinux:latest
# container, generates .SRCINFO, runs makepkg on the x86_64 source (the .deb
# and the license are placed next to the PKGBUILD, so makepkg verifies the
# checksums without downloading), runs namcap, installs the result and runs
# the same smoke test as verify.sh (SMOKE_DATA: the test documents). Writes
# <name>-bin-<version>-aur.tar.gz holding PKGBUILD and .SRCINFO, ready to
# push to the AUR.
#
# RELEASE_TAG: the release the .debs are attached to. Suite tags (v0.1.1)
# are not the Studio version (0.1.2), so it has to be given; without one
# (pull requests) v<version> stands in.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
[ $# -eq 3 ] || { echo "usage: $0 <amd64.deb> <arm64.deb> <outdir>" >&2; exit 2; }
deb_amd64="$(readlink -f "$1")"; deb_arm64="$(readlink -f "$2")"
mkdir -p "$3"; out="$(cd "$3" && pwd)"
# shellcheck source=/dev/null
. "$here/../linux-distros/distro.conf"
: "${VERSION:?set VERSION}"
: "${GITHUB_REPO:?distro.conf must set GITHUB_REPO, e.g. Dhiva-Labs/BranchPilot}"
: "${SMOKE_DATA:?set SMOKE_DATA to the directory of test documents}"
SMOKE_DATA="$(cd "$SMOKE_DATA" && pwd)"
tag="${RELEASE_TAG:-v$VERSION}"

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
deps=""; for d in "${ARCH_DEPENDS[@]}"; do deps+="'$d' "; done
sed -e "s|@NAME@|$NAME|g" -e "s|@VERSION@|$VERSION|g" \
    -e "s|@SUMMARY@|${SUMMARY//\'/}|g" -e "s|@HOMEPAGE@|$HOMEPAGE|g" \
    -e "s|@LICENSE@|$LICENSE|g" -e "s|@ARCH_DEPENDS@|${deps% }|g" \
    -e "s|@RELEASE_URL@|https://github.com/$GITHUB_REPO/releases/download/$tag|g" \
    -e "s|@GITHUB_REPO@|$GITHUB_REPO|g" -e "s|@TAG@|$tag|g" \
    -e "s|@SHA_LICENSE@|$(sha256sum "$repo/LICENSE" | cut -d' ' -f1)|g" \
    -e "s|@DEB_AMD64@|$(basename "$deb_amd64")|g" -e "s|@DEB_ARM64@|$(basename "$deb_arm64")|g" \
    -e "s|@SHA_AMD64@|$(sha256sum "$deb_amd64" | cut -d' ' -f1)|g" \
    -e "s|@SHA_ARM64@|$(sha256sum "$deb_arm64" | cut -d' ' -f1)|g" \
    "$here/PKGBUILD.in" > "$work/PKGBUILD"
cp "$deb_amd64" "$work/"
cp "$repo/LICENSE" "$work/markdrop-LICENSE-$tag"
if grep -n '@[A-Z0-9_]*@' "$work/PKGBUILD"; then echo "unfilled placeholder" >&2; exit 1; fi

docker run --rm -v "$work:/build" -v "$here/../linux-distros:/linux-distros:ro" \
  -v "$SMOKE_DATA:/smoke-data:ro" archlinux:latest bash -euo pipefail -c '
  . /linux-distros/distro.conf
  pacman -Syu --noconfirm --needed -q base-devel namcap \
    xorg-server-xvfb xorg-xauth mesa dbus python
  useradd -m builder
  chown -R builder /build
  cd /build
  su builder -c "makepkg --printsrcinfo > .SRCINFO"
  su builder -c "makepkg --noconfirm --nodeps -f"
  namcap PKGBUILD
  pacman -U --noconfirm ./*-x86_64.pkg.tar.zst
  export HOME=/tmp/smoke-home
  mkdir -p "$HOME"
  bash -c "$SMOKE_CMD"
  cat .SRCINFO
'
tar -C "$work" -czf "$out/$NAME-bin-$VERSION-aur.tar.gz" PKGBUILD .SRCINFO
ls -l "$out/$NAME-bin-$VERSION-aur.tar.gz"
