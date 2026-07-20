// YouTube -> Markdown without visiting the page: fetch watch HTML, parse
// ytInitialPlayerResponse for metadata + caption tracks, fetch the transcript.
// All fetches ride on the extension's youtube.com host permission.

export const YOUTUBE_URL_RE =
  /^https?:\/\/(www\.|m\.)?(youtube\.com\/(watch\?|shorts\/)|youtu\.be\/)/i;

export function extractVideoId(url) {
  const m = url.match(/(?:v=|youtu\.be\/|shorts\/)([A-Za-z0-9_-]{11})/);
  return m ? m[1] : null;
}

// Parse the ytInitialPlayerResponse JSON object out of watch-page HTML.
export function parsePlayerResponse(html) {
  const marker = "ytInitialPlayerResponse = ";
  const start = html.indexOf(marker);
  if (start === -1) return null;
  const jsonStart = start + marker.length;
  // Walk to the matching closing brace of the JSON object
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = jsonStart; i < html.length; i++) {
    const ch = html[i];
    if (escape) { escape = false; continue; }
    if (ch === "\\") { escape = true; continue; }
    if (ch === '"') { inString = !inString; continue; }
    if (inString) continue;
    if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) {
        try {
          return JSON.parse(html.slice(jsonStart, i + 1));
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

export function metadataFromPlayerResponse(pr) {
  const details = pr?.videoDetails || {};
  return {
    title: details.title || null,
    channel: details.author || null,
    description: details.shortDescription || null,
    lengthSeconds: details.lengthSeconds ? Number(details.lengthSeconds) : null,
    viewCount: details.viewCount || null,
  };
}

export function captionTrackUrl(pr, preferredLangs = ["en"]) {
  const tracks =
    pr?.captions?.playerCaptionsTracklistRenderer?.captionTracks || [];
  if (!tracks.length) return null;
  for (const lang of preferredLangs) {
    const exact = tracks.find((t) => t.languageCode === lang && !t.kind);
    if (exact) return exact.baseUrl;
  }
  for (const lang of preferredLangs) {
    const any = tracks.find((t) => (t.languageCode || "").startsWith(lang));
    if (any) return any.baseUrl;
  }
  return tracks[0].baseUrl;
}

// json3 transcript format -> [{start, text}]
export function parseJson3Transcript(json) {
  const out = [];
  for (const ev of json?.events || []) {
    if (!ev.segs) continue;
    const text = ev.segs.map((s) => s.utf8 || "").join("").replace(/\n/g, " ").trim();
    if (text) out.push({ start: (ev.tStartMs || 0) / 1000, text });
  }
  return out;
}

export function formatTimestamp(totalSeconds) {
  const t = Math.floor(totalSeconds);
  const h = String(Math.floor(t / 3600)).padStart(2, "0");
  const m = String(Math.floor((t % 3600) / 60)).padStart(2, "0");
  const s = String(t % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

export function buildVideoMarkdown(meta, transcript, { timestamps = false } = {}) {
  const lines = ["# YouTube", ""];
  if (meta.title) lines.push(`## ${meta.title}`, "");
  const facts = [];
  if (meta.channel) facts.push(`- **Channel:** ${meta.channel}`);
  if (meta.lengthSeconds) facts.push(`- **Duration:** ${formatTimestamp(meta.lengthSeconds)}`);
  if (meta.viewCount) facts.push(`- **Views:** ${meta.viewCount}`);
  if (facts.length) lines.push("### Video Metadata", ...facts, "");
  if (meta.description) lines.push("### Description", meta.description.trim(), "");
  if (transcript && transcript.length) {
    lines.push("### Transcript");
    if (timestamps) {
      for (const seg of transcript) lines.push(`[${formatTimestamp(seg.start)}] ${seg.text}`);
    } else {
      lines.push(transcript.map((s) => s.text).join(" "));
    }
  } else {
    lines.push("*(No transcript available for this video.)*");
  }
  return lines.join("\n");
}

// Live path (used from popup): needs network access.
export async function fetchVideoMarkdown(url, { timestamps = false } = {}) {
  const id = extractVideoId(url);
  if (!id) throw new Error("Could not find a video id in that URL");
  const watchUrl = `https://www.youtube.com/watch?v=${id}`;
  const resp = await fetch(watchUrl, { credentials: "omit" });
  if (!resp.ok) throw new Error(`YouTube returned ${resp.status}`);
  const html = await resp.text();
  const pr = parsePlayerResponse(html);
  if (!pr) throw new Error("Could not parse video data (YouTube layout may have changed)");
  const meta = metadataFromPlayerResponse(pr);

  let transcript = null;
  const trackUrl = captionTrackUrl(pr);
  if (trackUrl) {
    const sep = trackUrl.includes("?") ? "&" : "?";
    const tResp = await fetch(`${trackUrl}${sep}fmt=json3`, { credentials: "omit" });
    if (tResp.ok) {
      try {
        transcript = parseJson3Transcript(await tResp.json());
      } catch {
        transcript = null;
      }
    }
  }
  return {
    title: meta.title,
    markdown: buildVideoMarkdown(meta, transcript, { timestamps }),
    source: watchUrl,
  };
}
