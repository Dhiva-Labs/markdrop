# Markdrop v0.1.1

The second suite release brings Markdrop Studio to Linux arm64 and to more Linux distributions, plus Markdrop Clipper 0.1.1 for Chrome and Firefox. Components keep their own version numbers; see `CHANGELOG.md` for the full list.

## What's new

### 🧩 Markdrop Clipper 0.1.1
- **Licence texts:** both packages now ship `THIRD_PARTY_NOTICES.md` and the licence texts of the bundled libraries (Mozilla Readability, Turndown, turndown-plugin-gfm), plus Clipper's own MIT licence.
- **Firefox:** the package declares that it collects no data, which addons.mozilla.org requires of new add-ons, so it now needs **Firefox 140 or later**. It is in review on addons.mozilla.org.
- **Chrome:** the 0.1.1 update is in review on the Chrome Web Store.
- Conversion behaviour is unchanged from 0.1.0.

### 🖥️ Markdrop Studio 0.1.2 for Linux
- **Packages:** `.deb` for **amd64 and arm64**. Each architecture also gets an `.rpm` (Fedora, RHEL, openSUSE), an **Arch** package, an **AppImage**, a **Flatpak** bundle (`com.dhivalabs.MarkdropStudio`) and an **AUR** PKGBUILD (`markdrop-studio-bin`).
- **Testing:** every package is installed on its own distribution in CI and passes the app's self-test there.
- **Attaching:** CI builds these and attaches them to this release shortly after it is published, with their checksums in `SHA256SUMS-studio-linux.txt`.

### Unchanged
- Markdrop Mobile 0.1.0 APK and markdrop-mcp 0.1.0 are the same files as in v0.1.0, carried over so this release is complete.
- Markdrop Web and the Telegram bot have the same code as v0.1.0.

## Downloads

| Asset | Install |
|---|---|
| `markdrop-clipper-chrome-0.1.1.zip` | `chrome://extensions` → Developer mode → **Load unpacked** (after unzipping) |
| `markdrop-clipper-firefox-0.1.1.zip` | `about:debugging` → **This Firefox** → **Load Temporary Add-on** (Firefox 140+) |
| `markdrop-studio_0.1.2_amd64.deb` / `_arm64.deb` | `sudo apt install ./markdrop-studio_0.1.2_<arch>.deb`, then launch **Markdrop Studio** or run `markdrop` |
| `.rpm`, Arch package, AppImage, Flatpak, AUR PKGBUILD | Attached by CI; pick the file for your distribution and architecture |
| `markdrop-mobile-0.1.0.apk` | `adb install markdrop-mobile-0.1.0.apk` (arm64/x86_64, Android 7+) |
| `markdrop_mcp-0.1.0-py3-none-any.whl` | `pip install markdrop_mcp-0.1.0-py3-none-any.whl`, then `claude mcp add markdrop -- markdrop-mcp --root ~/your-folder` |

Checksums: `SHA256SUMS.txt` (files uploaded with the release) and `SHA256SUMS-studio-linux.txt` (Studio packages from CI). Verify with `sha256sum -c`.
