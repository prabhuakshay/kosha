// Loaded blocking in <head>, so it hears the first tap. htmx swaps each page
// in inside a view transition; on a phone, going deeper slides the new screen
// in and going back slides it away, as a navigation stack would. Everything
// else, such as a tab, switches at once, as native tab bars do.
const SLIDES = matchMedia("(max-width: 767px) and (prefers-reduced-motion: no-preference)");
let direction = null;

addEventListener("click", (event) => {
  const link = event.target.closest("[data-up], .row");
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
