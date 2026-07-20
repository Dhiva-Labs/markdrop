// Shared markdown pipeline: Turndown configured to mirror markitdown's
// _CustomMarkdownify conventions (ATX headings, no javascript: links,
// truncated data: URIs, checkbox syntax).

import TurndownService from "turndown";
import { gfm } from "turndown-plugin-gfm";

export function createTurndown({ keepDataUris = false } = {}) {
  const td = new TurndownService({
    headingStyle: "atx",
    hr: "---",
    bulletListMarker: "-",
    codeBlockStyle: "fenced",
    emDelimiter: "*",
  });
  td.use(gfm);

  // Strip javascript: and other non-http(s)/file link schemes
  td.addRule("safeLinks", {
    filter: (node) =>
      node.nodeName === "A" && node.getAttribute("href"),
    replacement: (content, node) => {
      const href = node.getAttribute("href") || "";
      let scheme = "";
      const m = href.match(/^([a-zA-Z][a-zA-Z0-9+.-]*):/);
      if (m) scheme = m[1].toLowerCase();
      if (scheme && !["http", "https", "file"].includes(scheme)) {
        return content;
      }
      if (!content.trim()) return "";
      const title = node.getAttribute("title");
      const titlePart = title ? ` "${title.replace(/"/g, '\\"')}"` : "";
      return `[${content}](${href}${titlePart})`;
    },
  });

  // Truncate data: URI images unless configured otherwise
  td.addRule("images", {
    filter: "img",
    replacement: (_content, node) => {
      const alt = (node.getAttribute("alt") || "").replace(/\n/g, " ");
      let src = node.getAttribute("src") || node.getAttribute("data-src") || "";
      if (src.startsWith("data:") && !keepDataUris) {
        src = src.split(",")[0] + "...";
      }
      const title = node.getAttribute("title");
      const titlePart = title ? ` "${title.replace(/"/g, '\\"')}"` : "";
      return src ? `![${alt}](${src}${titlePart})` : alt;
    },
  });

  // Checkboxes -> [x] / [ ]
  td.addRule("checkboxes", {
    filter: (node) =>
      node.nodeName === "INPUT" && node.getAttribute("type") === "checkbox",
    replacement: (_content, node) =>
      node.hasAttribute("checked") ? "[x] " : "[ ] ",
  });

  return td;
}

export function htmlToMarkdown(html, opts = {}) {
  const td = createTurndown(opts);
  return normalize(td.turndown(html));
}

export function normalize(markdown) {
  return markdown
    .split(/\r?\n/)
    .map((line) => line.replace(/\s+$/, ""))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function frontMatter({ title, source }) {
  const lines = ["---"];
  const safeTitle = (title || "").replace(/\n/g, " ").trim();
  if (safeTitle) lines.push(`title: ${safeTitle}`);
  lines.push(`source: ${source}`);
  lines.push(`converted: ${new Date().toISOString().slice(0, 10)}`);
  lines.push("generator: dhiva-labs/markdrop-clipper");
  lines.push("---");
  return lines.join("\n");
}

export function composeDocument({ title, source, markdown, withFrontMatter = true }) {
  const body = normalize(markdown);
  return withFrontMatter
    ? `${frontMatter({ title, source })}\n\n${body}\n`
    : body + "\n";
}

export function filenameFor(title, fallback = "converted") {
  const base = (title || fallback)
    .replace(/[^\w\d-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
  return (base || fallback) + ".md";
}
