# Permission justifications (paste into the CWS "Privacy practices" tab)

**Single purpose description:**
Markdrop Clipper converts web pages, selections, images and YouTube videos into Markdown files, locally in the browser.

| Permission | Justification |
|---|---|
| `activeTab` | Read the current page's content only when the user clicks the toolbar button, a context-menu item, or the keyboard shortcut, in order to convert that page to Markdown. |
| `scripting` | Inject the conversion script (Readability + Turndown) and the element-picker overlay into the active tab, on user action only. |
| `contextMenus` | Provide "Convert page / selection / image / link" right-click entries. |
| `downloads` | Save the converted Markdown as a .md file when the user clicks Download. |
| `storage` | Store the user's settings (front-matter toggle, filename options, optional self-hosted API endpoint). No browsing data is stored. |
| `clipboardWrite` | Copy the converted Markdown to the clipboard when the user clicks Copy. |
| Host permission `https://www.youtube.com/*`, `https://m.youtube.com/*` | Fetch video metadata and caption tracks so a pasted YouTube link can be converted to a Markdown transcript without opening the page. |

**Remote code:** none — all code is packaged in the extension.

**Data usage disclosures:** the extension does not collect, transmit, sell, or share any user data. All conversion happens locally. (Tick "No" to all data-collection categories.)
