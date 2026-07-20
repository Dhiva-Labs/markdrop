// Service worker: context menus, downloads, keyboard command, API relay.

import { composeDocument, filenameFor } from "./lib/markdown.js";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "convert-page", title: "Convert page to Markdown", contexts: ["page"] });
  chrome.contextMenus.create({ id: "convert-selection", title: "Convert selection to Markdown", contexts: ["selection"] });
  chrome.contextMenus.create({ id: "copy-image-md", title: "Copy image as Markdown", contexts: ["image"] });
  chrome.contextMenus.create({ id: "pick-element", title: "Select element to convert…", contexts: ["page"] });
  chrome.contextMenus.create({ id: "convert-link", title: "Convert link target to Markdown (via API)", contexts: ["link"] });
});

// Linked .pdf/.docx/etc. go through the project-04 Conversion API.
async function convertLinkViaApi(linkUrl) {
  const { apiUrl, apiKey } = await chrome.storage.sync.get({ apiUrl: "", apiKey: "" });
  if (!apiUrl) {
    notify("Set the Conversion API endpoint in Options first.");
    return;
  }
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["X-API-Key"] = apiKey;
  const resp = await fetch(`${apiUrl.replace(/\/$/, "")}/api/convert/url`, {
    method: "POST",
    headers,
    body: JSON.stringify({ url: linkUrl }),
  });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok || !body.ok) {
    notify(body.error || body.detail || `API error ${resp.status}`);
    return;
  }
  download(filenameFor(body.title, "linked"), body.markdown);
}

async function ensureExtract(tabId) {
  await chrome.scripting.executeScript({ target: { tabId }, files: ["content/extract.js"] });
}

async function extractAndDownload(tabId, mode) {
  await ensureExtract(tabId);
  const res = await chrome.tabs.sendMessage(tabId, { type: "md-extract", mode });
  if (!res || res.error) {
    notify(res?.error || "Conversion failed");
    return;
  }
  const doc = composeDocument({ title: res.title, source: res.source, markdown: res.markdown });
  download(filenameFor(res.title), doc);
}

function download(filename, content) {
  const url = "data:text/markdown;charset=utf-8," + encodeURIComponent(content);
  chrome.downloads.download({ url, filename, saveAs: true });
}

function notify(message) {
  // Badge flash as a lightweight, permission-free signal
  chrome.action.setBadgeText({ text: "!" });
  chrome.action.setBadgeBackgroundColor({ color: "#b42318" });
  setTimeout(() => chrome.action.setBadgeText({ text: "" }), 4000);
  console.warn("[MD Clipper]", message);
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab?.id) return;
  try {
    if (info.menuItemId === "convert-page") await extractAndDownload(tab.id, "article");
    if (info.menuItemId === "convert-selection") await extractAndDownload(tab.id, "selection");
    if (info.menuItemId === "pick-element") {
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content/picker.js"] });
    }
    if (info.menuItemId === "convert-link" && info.linkUrl) {
      await convertLinkViaApi(info.linkUrl);
    }
    if (info.menuItemId === "copy-image-md") {
      const alt = (info.altText || "").replace(/\n/g, " ");
      const md = `![${alt}](${info.srcUrl})`;
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        args: [md],
        func: (text) => navigator.clipboard.writeText(text),
      });
    }
  } catch (e) {
    notify(String(e?.message || e));
  }
});

chrome.commands.onCommand.addListener(async (command, tab) => {
  if (command === "convert-article" && tab?.id) {
    await extractAndDownload(tab.id, "article");
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "md-download") {
    download(msg.filename || "converted.md", msg.content || "");
    sendResponse({ ok: true });
  }
  return undefined;
});
