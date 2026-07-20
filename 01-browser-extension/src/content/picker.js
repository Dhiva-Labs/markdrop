// Element picker: hover-highlight DOM blocks, click to select, shift-click to
// multi-select, Enter to convert, Esc to cancel. After conversion an in-page
// toolbar offers Copy / Download. No iframes (CSP-safe), plain positioned divs.

import { htmlToMarkdown, composeDocument, filenameFor } from "../lib/markdown.js";

(() => {
  if (window.__mdClipperPickerActive) return;
  window.__mdClipperPickerActive = true;

  const Z = 2147483600;
  const picked = new Set();
  let hoverEl = null;

  const overlay = box("rgba(99,102,241,.25)", "2px solid #6366f1");
  const style = document.createElement("style");
  style.textContent = `
    .md-clip-picked-outline { outline: 3px solid #12805c !important; outline-offset: 1px; }
    .md-clip-bar { position: fixed; z-index: ${Z + 2}; left: 50%; transform: translateX(-50%);
      bottom: 18px; background: #171b23; color: #e6e9ef; border-radius: 12px;
      padding: 10px 14px; font: 13px/1.4 system-ui, sans-serif; display: flex; gap: 10px;
      align-items: center; box-shadow: 0 8px 30px rgba(0,0,0,.45); }
    .md-clip-bar button { background: #6366f1; color: #fff; border: 0; border-radius: 8px;
      padding: 7px 14px; font: inherit; cursor: pointer; }
    .md-clip-bar button.secondary { background: #2a3040; }
  `;
  document.documentElement.appendChild(style);

  const bar = document.createElement("div");
  bar.className = "md-clip-bar";
  bar.innerHTML = `<span>Click a block to select · Shift-click adds more · </span>
    <button data-act="done">Convert</button>
    <button class="secondary" data-act="cancel">Cancel (Esc)</button>`;
  document.documentElement.appendChild(bar);

  function box(bg, border) {
    const el = document.createElement("div");
    el.style.cssText = `position:absolute; z-index:${Z}; pointer-events:none; background:${bg}; border:${border}; border-radius:4px; display:none;`;
    document.documentElement.appendChild(el);
    return el;
  }

  function positionOver(el, target) {
    const r = target.getBoundingClientRect();
    el.style.display = "block";
    el.style.left = r.left + scrollX + "px";
    el.style.top = r.top + scrollY + "px";
    el.style.width = r.width + "px";
    el.style.height = r.height + "px";
  }

  function candidate(el) {
    // Walk up from tiny inline nodes to a meaningful block
    let node = el;
    while (
      node &&
      node !== document.body &&
      (node.matches?.("a, span, b, i, em, strong, code, img, svg *") ||
        (node.getBoundingClientRect?.().height ?? 0) < 14)
    ) {
      node = node.parentElement;
    }
    return node && node !== document.documentElement ? node : null;
  }

  function onMove(e) {
    const el = candidate(document.elementFromPoint(e.clientX, e.clientY));
    if (!el || bar.contains(el)) { overlay.style.display = "none"; hoverEl = null; return; }
    hoverEl = el;
    positionOver(overlay, el);
  }

  function onClick(e) {
    if (bar.contains(e.target)) return; // toolbar handles itself
    e.preventDefault();
    e.stopPropagation();
    if (!hoverEl) return;
    if (!e.shiftKey) {
      for (const p of picked) p.classList.remove("md-clip-picked-outline");
      picked.clear();
    }
    if (picked.has(hoverEl)) {
      picked.delete(hoverEl);
      hoverEl.classList.remove("md-clip-picked-outline");
    } else {
      picked.add(hoverEl);
      hoverEl.classList.add("md-clip-picked-outline");
    }
  }

  function onKey(e) {
    if (e.key === "Escape") teardown();
    if (e.key === "Enter") convert();
  }

  function teardown() {
    window.__mdClipperPickerActive = false;
    document.removeEventListener("mousemove", onMove, true);
    document.removeEventListener("click", onClick, true);
    document.removeEventListener("keydown", onKey, true);
    for (const p of picked) p.classList.remove("md-clip-picked-outline");
    overlay.remove();
    bar.remove();
    style.remove();
  }

  function convert() {
    if (!picked.size && hoverEl) { picked.add(hoverEl); }
    if (!picked.size) return;
    const holder = document.implementation.createHTMLDocument("");
    for (const el of picked) {
      const clone = el.cloneNode(true);
      clone.classList?.remove("md-clip-picked-outline");
      holder.body.appendChild(clone);
    }
    for (const a of holder.querySelectorAll("a[href]")) {
      try { a.setAttribute("href", new URL(a.getAttribute("href"), location.href).href); } catch { /* keep */ }
    }
    for (const img of holder.querySelectorAll("img[src]")) {
      try { img.setAttribute("src", new URL(img.getAttribute("src"), location.href).href); } catch { /* keep */ }
    }
    const markdown = htmlToMarkdown(holder.body.innerHTML);
    const doc = composeDocument({ title: document.title, source: location.href, markdown });
    showResult(doc);
  }

  function showResult(doc) {
    bar.innerHTML = `<span>${doc.length.toLocaleString()} chars of Markdown · </span>
      <button data-act="copy">Copy</button>
      <button data-act="download">Download .md</button>
      <button class="secondary" data-act="cancel">Close</button>`;
    bar.dataset.result = "1";
    bar.__doc = doc;
    overlay.style.display = "none";
    document.removeEventListener("mousemove", onMove, true);
    document.removeEventListener("click", onClick, true);
  }

  bar.addEventListener("click", async (e) => {
    const act = e.target?.dataset?.act;
    if (!act) return;
    e.stopPropagation();
    if (act === "cancel") teardown();
    if (act === "done") convert();
    if (act === "copy") {
      await navigator.clipboard.writeText(bar.__doc);
      e.target.textContent = "Copied ✓";
    }
    if (act === "download") {
      chrome.runtime.sendMessage({
        type: "md-download",
        filename: filenameFor(document.title, "clip"),
        content: bar.__doc,
      });
      e.target.textContent = "Saved ✓";
    }
  });

  document.addEventListener("mousemove", onMove, true);
  document.addEventListener("click", onClick, true);
  document.addEventListener("keydown", onKey, true);
})();
