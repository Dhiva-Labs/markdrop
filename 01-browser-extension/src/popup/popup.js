import { composeDocument, filenameFor } from "../lib/markdown.js";
import { fetchVideoMarkdown, YOUTUBE_URL_RE } from "../lib/youtube.js";

const $ = (id) => document.getElementById(id);
let lastDoc = null;
let lastTitle = null;

function status(msg, cls = "") {
  $("status").textContent = msg;
  $("status").className = cls;
}

function showDoc(title, doc) {
  lastDoc = doc;
  lastTitle = title;
  $("out").classList.add("show");
  $("md").value = doc;
  status(`Done — ${doc.length.toLocaleString()} characters`, "ok");
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function convertPage(mode) {
  const tab = await activeTab();
  if (!tab?.id || !/^https?:/.test(tab.url || "")) {
    status("This page cannot be converted.", "err");
    return;
  }
  status("Converting…");
  try {
    const settings = await chrome.storage.sync.get({ frontMatter: true, keepDataUris: false });
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content/extract.js"] });
    const res = await chrome.tabs.sendMessage(tab.id, {
      type: "md-extract",
      mode,
      options: { keepDataUris: settings.keepDataUris },
    });
    if (!res || res.error) throw new Error(res?.error || "No response from page");
    const doc = composeDocument({
      title: res.title,
      source: res.source,
      markdown: res.markdown,
      withFrontMatter: settings.frontMatter,
    });
    showDoc(res.title, doc);
  } catch (e) {
    status(String(e?.message || e), "err");
  }
}

$("btn-article").addEventListener("click", () => convertPage("article"));
$("btn-full").addEventListener("click", () => convertPage("full"));
$("btn-selection").addEventListener("click", () => convertPage("selection"));

$("btn-picker").addEventListener("click", async () => {
  const tab = await activeTab();
  if (!tab?.id) return;
  await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content/picker.js"] });
  window.close(); // picker takes over in-page
});

$("btn-yt").addEventListener("click", async () => {
  const url = $("yt-url").value.trim();
  if (!YOUTUBE_URL_RE.test(url)) {
    status("Paste a YouTube watch/shorts URL first.", "err");
    return;
  }
  status("Fetching video + transcript…");
  try {
    const settings = await chrome.storage.sync.get({ frontMatter: true });
    const res = await fetchVideoMarkdown(url, { timestamps: $("yt-ts").checked });
    const doc = composeDocument({
      title: res.title,
      source: res.source,
      markdown: res.markdown,
      withFrontMatter: settings.frontMatter,
    });
    showDoc(res.title, doc);
  } catch (e) {
    status(String(e?.message || e), "err");
  }
});

$("btn-copy").addEventListener("click", async () => {
  if (lastDoc) {
    await navigator.clipboard.writeText(lastDoc);
    status("Copied to clipboard", "ok");
  }
});

$("btn-dl").addEventListener("click", () => {
  if (!lastDoc) return;
  chrome.runtime.sendMessage({
    type: "md-download",
    filename: filenameFor(lastTitle),
    content: lastDoc,
  });
});

$("open-options").addEventListener("click", () => chrome.runtime.openOptionsPage());

// Prefill the YouTube box when the current tab is a YouTube page
activeTab().then((tab) => {
  if (tab?.url && YOUTUBE_URL_RE.test(tab.url)) $("yt-url").value = tab.url;
});
