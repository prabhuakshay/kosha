// htmx swaps each page's body in, so what each page needs is set up again
// after every swap.
function setUp() {
  lucide.createIcons();
  writeAmounts();
  titleBars();
  openSheets();
  closeMenus();
}
setUp();
document.addEventListener("htmx:afterSwap", setUp);

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

// The server can't tell where the browser is, and the Owner's Time zone is
// guessed from it until they set one (core/time_zone.py).
document.cookie = `time_zone=${Intl.DateTimeFormat().resolvedOptions().timeZone}; path=/; max-age=34560000; samesite=lax`;

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

// Whole rupees drop their ".00"; paise that matter stay, dimmed.
function writeAmounts() {
  for (const el of document.querySelectorAll(".amount:not([data-written])")) {
    el.dataset.written = "";
    const text = el.textContent.trim();
    const match = text.match(/^(.*)\.(\d+)$/);
    if (!match) continue;
    if (/^0+$/.test(match[2])) {
      el.textContent = match[1];
    } else {
      const paise = document.createElement("span");
      paise.className = "paise";
      paise.textContent = `.${match[2]}`;
      el.replaceChildren(match[1], paise);
    }
  }
}

// A pane's bar takes its title once the large one scrolls away, as on iOS.
function titleBars() {
  for (const pane of document.querySelectorAll(".pane")) {
    const bar = pane.querySelector(".bar");
    const heading = pane.querySelector(".title, .hero h1, .empty h1");
    if (!bar || !heading) continue;
    bar.querySelector(".bar-title").textContent = heading.textContent;
    new IntersectionObserver(([entry]) => {
      bar.classList.toggle("collapsed", !entry.isIntersecting && entry.boundingClientRect.top < 100);
    }, { rootMargin: "-60px 0px 0px 0px" }).observe(heading);
  }
}

// On a phone a menu covers the screen, so a tap outside its card closes it
// rather than landing on the page behind. iOS fires a tap's click only on
// an element listening for it itself, so a listener on the document misses it.
function closeMenus() {
  for (const menu of document.querySelectorAll("[popover].menu:not([data-closes])")) {
    menu.dataset.closes = "";
    menu.addEventListener("click", (event) => {
      if (event.target === menu) menu.hidePopover();
    });
  }
}

// A sheet is a page's form, opened over it; closing it goes back to the page.
function openSheets() {
  for (const sheet of document.querySelectorAll("dialog[data-open]:not([open])")) {
    sheet.showModal();
    // Changing something waits for a tap, rather than raising the keyboard.
    if (!sheet.querySelector("[autofocus]")) sheet.focus();
    const dismiss = () => sheet.querySelector("[data-dismiss]").click();
    sheet.addEventListener("cancel", (event) => {
      event.preventDefault();
      dismiss();
    });
    sheet.addEventListener("click", (event) => {
      if (event.target === sheet) dismiss();
    });
  }
}

document.addEventListener("keydown", (event) => {
  // ⌘↵ or Ctrl↵ sends a sheet's form.
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    document.querySelector("dialog[open] form")?.requestSubmit();
    return;
  }
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.target.closest("input, textarea, select, [contenteditable]")) return;
  if (document.querySelector("dialog[open], :popover-open")) return;

  // j and k step through a list pane's rows, as in a mail app.
  const by = { j: 1, k: -1 }[event.key];
  if (by) {
    const rows = [...document.querySelectorAll(".split-list a.row")];
    if (!rows.length) return;
    const at = rows.findIndex((row) => row.hasAttribute("aria-current"));
    const next = rows[at === -1 ? 0 : Math.min(rows.length - 1, Math.max(0, at + by))];
    if (next !== rows[at]) next.click();
    return;
  }

  // Everything else with a shortcut says so in its data-key.
  const target = [...document.querySelectorAll("[data-key]")].find(
    (el) => el.dataset.key === event.key.toLowerCase() && el.getClientRects().length,
  );
  if (target) {
    event.preventDefault();
    target.click();
  }
});
