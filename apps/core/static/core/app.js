lucide.createIcons();

for (const button of document.querySelectorAll("[data-copy]")) {
  button.addEventListener("click", () => {
    navigator.clipboard.writeText(document.getElementById(button.dataset.copy).innerText);
  });
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register(document.currentScript.dataset.serviceWorker);
}
