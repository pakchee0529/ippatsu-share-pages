const CACHE_NAME = "photo-ledger-poc0-09391fe461b98ee3";
const ASSETS = [
  "./",
  "./index.html",
  "./app.js",
  "./styles.css",
  "./pack.js",
  "./release-manifest.json",
  "./qrcode.js",
  "./qrcode_UTF8.js",
  "./manifest.webmanifest",
  "./icon-192.png",
  "./icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const path = new URL(event.request.url).pathname;
  // A new PWA shell must never keep interpreting an old date pack while the
  // handset is online.  Offline use remains safe because a network failure
  // falls back to the last verified cached pack.
  if (path.endsWith("/pack.js") || path.endsWith("/release-manifest.json")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
