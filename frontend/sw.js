const CACHE = "mirror-v6";
const ASSETS = ["/", "/app.js", "/styles.css", "/tailwind.css", "/assets/mira.png"];

// Precarga tolerante: un asset ausente no aborta la instalación del SW.
self.addEventListener("install", e => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE).then(c => Promise.allSettled(ASSETS.map(a => c.add(a))))
  );
});

// Limpia versiones de caché anteriores para que un deploy se vea de inmediato.
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = e.request.url;
  // El catálogo de emociones SÍ se cachea: red primero, caché como respaldo offline.
  if (url.includes("/api/emotions")) {
    e.respondWith(
      fetch(e.request).then(r => {
        const copy = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
        return r;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  if (url.includes("/api/")) return; // el resto de la API nunca se cachea
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
