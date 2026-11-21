const APP_CACHE = 'grafos-ut-app-v1';
const PYODIDE_CACHE = 'grafos-ut-pyodide-v1';

const APP_ASSETS = [
  './',
  './index.html',
  './motor.py',
  './manifest.json',
  './logo-ut.png',
  './icon-192.png',
  './icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_CACHE)
      .then((cache) => cache.addAll(APP_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((k) => k !== APP_CACHE && k !== PYODIDE_CACHE)
          .map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Pyodide desde CDN: Cache-First (una vez descargado funciona offline)
  if (url.origin === 'https://cdn.jsdelivr.net' && url.pathname.includes('/pyodide/')) {
    event.respondWith(
      caches.open(PYODIDE_CACHE).then((cache) =>
        cache.match(request).then((cached) => {
          if (cached) return cached;
          return fetch(request).then((response) => {
            if (response && (response.ok || response.type === 'opaque')) {
              cache.put(request, response.clone());
            }
            return response;
          });
        })
      )
    );
    return;
  }

  // Archivos locales de Grafos UT: Network-First con respaldo offline en caché
  if (url.origin === self.location.origin) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches.open(APP_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() =>
          caches.match(request).then((cached) => {
            if (cached) return cached;
            if (request.mode === 'navigate') return caches.match('./index.html');
            return new Response('Sin conexión y recurso no disponible en caché.', {
              status: 503,
              statusText: 'Offline'
            });
          })
        )
    );
  }
});
