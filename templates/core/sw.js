// Kosha's service worker. It has no fetch handler and stores nothing, so every
// page comes from the server. Push handlers land here with notifications.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
