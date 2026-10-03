lucide.createIcons();

for (const button of document.querySelectorAll("[data-copy]")) {
  button.addEventListener("click", () => {
    navigator.clipboard.writeText(document.getElementById(button.dataset.copy).innerText);
  });
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register(document.currentScript.dataset.serviceWorker);
}

// j and k step through a list pane's rows, as in a mail app.
const rows = [...document.querySelectorAll(".split-list .row")];
document.addEventListener("keydown", (event) => {
  const by = { j: 1, k: -1 }[event.key];
  if (!by || !rows.length || event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.target.closest("input, textarea, select, [contenteditable]")) return;
  const at = rows.findIndex((row) => row.hasAttribute("aria-current"));
  const next = rows[at === -1 ? 0 : Math.min(rows.length - 1, Math.max(0, at + by))];
  if (next !== rows[at]) location.assign(next.href);
});
