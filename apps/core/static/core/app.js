lucide.createIcons();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register(document.currentScript.dataset.serviceWorker);
}
