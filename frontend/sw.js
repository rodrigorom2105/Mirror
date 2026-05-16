const CACHE = "mirror-v2";
const ASSETS = ["/", "/app.js", "/styles.css"];

self.addEventListener("install", e =>
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)))
);

self.addEventListener("fetch", e => {
  if (e.request.url.includes("/api/")) return; // never cache API calls
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
