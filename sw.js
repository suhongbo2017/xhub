// X-HUB Service Worker v1.0.0
const CACHE_NAME = 'xhub-v7';
const OLD_CACHE_NAMES = [
  'xhub-v1',
  'xhub-v2',
  'xhub-v3',
  'xhub-v4',
  'xhub-v5',
  'xhub-v6'
];
const LOCAL_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/sw.js'
];

// Install: cache local assets only
self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(LOCAL_ASSETS);
    })
  );
});

// Activate: clean old caches immediately
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      const toDelete = names.filter(name => OLD_CACHE_NAMES.includes(name));
      return Promise.all(toDelete.map(name => caches.delete(name)));
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// Fetch: serve from cache for local, bypass API routes
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Bypass caching for API requests
  if (url.pathname.startsWith('/api/')) {
    return;
  }
  
  // Network first for HTML, cache fallback
  if (url.pathname.endsWith('.html') || url.pathname === '/') {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          // Update cache with fresh content
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
          return networkResponse;
        })
        .catch(() => {
          return caches.match(event.request);
        })
    );
    return;
  }
  
  // Cache first for static assets
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});

// Background sync for offline queue (future feature)
// self.addEventListener('sync', (event) => {});
