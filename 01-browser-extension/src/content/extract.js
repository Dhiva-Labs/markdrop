// Injected on demand. Answers "md-extract" messages with converted markdown.
// Runs entirely in the page: Readability for article mode, Turndown for html->md.

import { Readability } from "@mozilla/readability";
import { htmlToMarkdown } from "../lib/markdown.js";

if (!window.__mdClipperExtractReady) {
  window.__mdClipperExtractReady = true;

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type !== "md-extract") return undefined;
    try {
      sendResponse(extract(msg.mode || "article", msg.options || {}));
    } catch (e) {
      sendResponse({ error: String(e && e.message ? e.message : e) });
    }
    return undefined; // synchronous response
  });

  function absolutize(doc) {
    for (const el of doc.querySelectorAll("a[href]")) {
      try { el.setAttribute("href", new URL(el.getAttribute("href"), location.href).href); } catch { /* keep as-is */ }
    }
    for (const el of doc.querySelectorAll("img[src], img[data-src]")) {
      const attr = el.getAttribute("src") ? "src" : "data-src";
      try { el.setAttribute(attr, new URL(el.getAttribute(attr), location.href).href); } catch { /* keep as-is */ }
    }
    return doc;
  }

  function extract(mode, options) {
    const title = document.title || "";
    const source = location.href;

    if (mode === "selection") {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) return { error: "Nothing is selected on the page." };
      const container = document.createElement("div");
      for (let i = 0; i < sel.rangeCount; i++) {
        container.appendChild(sel.getRangeAt(i).cloneContents());
      }
      const holder = document.implementation.createHTMLDocument("");
      holder.body.appendChild(container);
      absolutize(holder);
      return { title, source, markdown: htmlToMarkdown(holder.body.innerHTML, options) };
    }

    if (mode === "full") {
      const clone = document.cloneNode(true);
      clone.querySelectorAll("script, style, noscript, template").forEach((n) => n.remove());
      absolutize(clone);
      return { title, source, markdown: htmlToMarkdown(clone.body ? clone.body.innerHTML : "", options) };
    }

    // article mode (default): Readability on a clone
    const clone = document.cloneNode(true);
    const article = new Readability(clone).parse();
    if (article && article.content) {
      const holder = document.implementation.createHTMLDocument("");
      holder.body.innerHTML = article.content;
      absolutize(holder);
      return {
        title: article.title || title,
        source,
        byline: article.byline || null,
        markdown: htmlToMarkdown(holder.body.innerHTML, options),
      };
    }
    // Fallback to full page if Readability found nothing
    return extract("full", options);
  }
}
