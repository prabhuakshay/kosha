// Loaded blocking in <head>, so it hears the first tap. htmx swaps each page
// in inside a view transition; on a phone, going deeper slides the new screen
// in and going back slides it away, as a navigation stack would. Everything
// else, such as a tab, switches at once, as native tab bars do.
const SLIDES = matchMedia("(max-width: 1023px) and (prefers-reduced-motion: no-preference)");
let direction = null;

addEventListener("click", (event) => {
  // A menu's rows open a sheet over the page, which doesn't go deeper.
  const link = event.target.closest("[data-up], a.row:not(.menu a)");
  direction = link && (link.matches("[data-up]") ? "back" : "forward");
});

document.addEventListener("htmx:beforeTransition", (event) => {
  if (!direction || !SLIDES.matches) {
    event.preventDefault();
    return;
  }
  document.documentElement.dataset.direction = direction;
  direction = null;
});
