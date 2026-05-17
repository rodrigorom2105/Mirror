const CACHE = "mirror-v3";
const ASSETS = ["/", "/app.js", "/styles.css", "/tailwind.css", "/assets/mira.png"];

// Precarga tolerante: un asset ausente (p. ej. la mascota aún no subida)
// no debe abortar la instalación del Service Worker.
self.addEventListener("install", e => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE).then(c => Promise.allSettled(ASSETS.map(a => c.add(a))))
  );
});

// Limpia versiones de caché anteriores para que un deploy nuevo se vea de inmediato.
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  if (e.request.url.includes("/api/")) return; // nunca cachear llamadas API
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
