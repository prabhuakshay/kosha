// htmx swaps each page's body in, so icons are drawn again after every swap.
lucide.createIcons();
document.addEventListener("htmx:afterSwap", () => lucide.createIcons());

// Swaps keep the stylesheet and scripts the app opened with. A page from a
// newer deploy names others, by their hashed filenames, so it loads afresh.
const ASSETS = "link[rel=stylesheet], script[src]";
const assets = (doc) =>
  [...doc.querySelectorAll(ASSETS)].map((e) => e.getAttribute("href") ?? e.getAttribute("src")).join();
const loaded = assets(document);
document.addEventListener("htmx:beforeSwap", (event) => {
  const { xhr, requestConfig } = event.detail;
  if (requestConfig?.verb !== "get") return;
  if (assets(new DOMParser().parseFromString(xhr.response, "text/html")) === loaded) return;
  event.detail.shouldSwap = false;
  location.assign(xhr.responseURL);
});

// Pages are no-store, but a browser may still restore one from its
// back/forward cache, showing a sign-in step that's done or a stale page.
addEventListener("pageshow", (event) => {
  if (event.persisted) location.reload();
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-copy]");
  if (button) navigator.clipboard.writeText(document.getElementById(button.dataset.copy).innerText);
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register(document.currentScript.dataset.serviceWorker);
}

// iOS scrolls the page up over the keyboard rather than shrinking it, which
// brings the tab bar up with it. The keyboard shrinks only what's visible, so
// a much shorter visible area, not zoomed in, means it's open.
visualViewport?.addEventListener("resize", () => {
  const open = visualViewport.scale === 1 && visualViewport.height < innerHeight * 0.75;
  document.documentElement.classList.toggle("keyboard", open);
});

// j and k step through a list pane's rows, as in a mail app.
document.addEventListener("keydown", (event) => {
  const by = { j: 1, k: -1 }[event.key];
  const rows = [...document.querySelectorAll(".split-list .row")];
  if (!by || !rows.length || event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.target.closest("input, textarea, select, [contenteditable]")) return;
  const at = rows.findIndex((row) => row.hasAttribute("aria-current"));
  const next = rows[at === -1 ? 0 : Math.min(rows.length - 1, Math.max(0, at + by))];
  if (next !== rows[at]) next.click();
});
