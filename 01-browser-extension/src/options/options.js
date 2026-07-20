const DEFAULTS = { frontMatter: true, keepDataUris: false, apiUrl: "", apiKey: "" };

const $ = (id) => document.getElementById(id);

chrome.storage.sync.get(DEFAULTS).then((s) => {
  $("frontMatter").checked = s.frontMatter;
  $("keepDataUris").checked = s.keepDataUris;
  $("apiUrl").value = s.apiUrl;
  $("apiKey").value = s.apiKey;
});

$("save").addEventListener("click", async () => {
  await chrome.storage.sync.set({
    frontMatter: $("frontMatter").checked,
    keepDataUris: $("keepDataUris").checked,
    apiUrl: $("apiUrl").value.trim(),
    apiKey: $("apiKey").value.trim(),
  });
  $("saved").textContent = "Saved ✓";
  setTimeout(() => ($("saved").textContent = ""), 2000);
});
