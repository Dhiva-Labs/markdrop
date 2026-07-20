# Chrome Web Store — publish checklist for Markdrop Clipper 0.1.0

Everything you need is in this folder. Steps marked 🧑 need you (account/payment/judgment); nothing else is missing.

## 0. What's in this folder
| File | Use |
|---|---|
| `markdrop-clipper-chrome-0.1.0.zip` | The package you upload (built from `dist/`, icons included) |
| `listing/description.md` | Name, short + detailed description, category — copy-paste |
| `listing/permissions-justifications.md` | Paste into the "Privacy practices" tab (one justification per permission) |
| `listing/privacy-policy.md` | Host this text publicly, paste its URL into the listing |
| `assets/screenshot-1-1280x800.png` | Required screenshot (upload at least this one) |
| `assets/promo-tile-440x280.png` | Small promo tile (optional but recommended) |
| `assets/icon128.png` / `icon512.png` | Already inside the zip; 512 handy for other stores |

## 1. 🧑 Developer account (one-time)
1. Go to https://chrome.google.com/webstore/devconsole
2. Sign in with the Google account you want to publish under (dhivakar1010@gmail.com).
3. Pay the one-time **$5** developer registration fee.

## 2. 🧑 Host the privacy policy
Any public URL works. Easiest options:
- Push the suite to GitHub and link the raw/blob URL of `listing/privacy-policy.md`, or
- Create a GitHub Gist with its contents and use the gist URL.

## 3. Create the item
1. Dev console → **+ New item** → upload `markdrop-clipper-chrome-0.1.0.zip`.
2. **Store listing tab** — from `listing/description.md`: detailed description, category *Productivity → Tools*, language English. Upload `screenshot-1-1280x800.png` and `promo-tile-440x280.png`.
3. **Privacy practices tab** — paste the single-purpose line + per-permission justifications from `listing/permissions-justifications.md`; answer **No** to all data-collection questions; certify compliance; paste the privacy-policy URL.
4. **Distribution tab** — Public, all regions (or your preference).

## 4. 🧑 Submit for review
Click **Submit for review**. Typical review time: a few hours to a few days. Extensions with host permissions (youtube.com) sometimes get a manual review — the justifications file covers exactly what reviewers ask about.

## 5. After approval
- The store listing URL will be `https://chromewebstore.google.com/detail/<id>` — save the id.
- Future updates: bump `version` in `manifest.json`, run `npm run build`, upload the new `dist-zips/md-clipper-chrome-<version>.zip`, submit.

## Known review-risk notes (all mitigated)
- **Remote code**: none — everything is bundled. ✔
- **Broad host access**: only youtube.com, justified for transcripts. ✔
- **Minimum functionality**: rich single-purpose tool. ✔
- If reviewers ask why `clipboardWrite` + `downloads`: both are user-initiated output actions (Copy / Download buttons).
