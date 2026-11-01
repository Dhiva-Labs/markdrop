# Markdrop Studio Flatpak

`com.dhivalabs.MarkdropStudio.yml` repackages the installed tree of the Studio
`.deb` that `.github/workflows/studio-linux.yml` builds: the workflow unpacks
the `.deb` into `tree/` (gitignored) and runs flatpak-builder in the
`ghcr.io/flathub-infra/flatpak-github-actions:gnome-51` container, once on
x86_64 and once on aarch64. The bundle (`markdrop-studio-<version>-<arch>.flatpak`)
is then installed on the Ubuntu runner with the GNOME 51 runtime from Flathub
and tested by `test-bundle.sh`: ldd of every ELF file inside the sandbox, the
app's `--selftest` on four documents, and the window staying up under Xvfb.

Install a bundle (the GNOME runtime comes from Flathub):

```bash
flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user ./markdrop-studio-<version>-x86_64.flatpak
flatpak run com.dhivalabs.MarkdropStudio
```

Sandbox permissions: display (Wayland, X11 fallback), GPU, network (web pages
and YouTube links are downloaded for conversion) and read-only access to the
home directory (files dropped on the window arrive as host paths). Converted
Markdown is saved through the file chooser portal.

## A Flathub submission would differ

- Flathub builds from sources it can fetch: replace the `tree` directory
  source with the release `.deb` (`type: file`, `url` + `sha256`, with
  `only-arches` per architecture) and unpack it in `build-commands`
  (`bsdtar -xf` the `.deb`, then its `data.tar.xz`), or build the Flutter app
  and the PyInstaller engine from source in the manifest.
- Flathub wants screenshots and an OARS rating that matches the app in the
  metainfo, and usually a narrower filesystem permission than `home:ro`
  (for example dropping it and relying on the document portal, once file
  drops are confirmed to arrive through it).
- The app id would need to be verified on Flathub for the `com.dhivalabs`
  domain.
