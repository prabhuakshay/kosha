// Loaded blocking in <head>: pagereveal fires before deferred scripts run.
const DIRECTION = "kosha.direction";

addEventListener("click", (event) => {
  const link = event.target.closest("[data-up], .row");
  if (link) sessionStorage.setItem(DIRECTION, link.matches("[data-up]") ? "back" : "forward");
});

addEventListener("pagereveal", (event) => {
  if (!event.viewTransition) return;
  let direction = sessionStorage.getItem(DIRECTION);
  sessionStorage.removeItem(DIRECTION);
  const activation = window.navigation?.activation;
  if (activation?.navigationType === "traverse" && activation.from) {
    direction = activation.entry.index < activation.from.index ? "back" : "forward";
  }
  if (direction) event.viewTransition.types.add(direction);
});
