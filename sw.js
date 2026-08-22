const CACHE_NAME = 'xhub-v7';
const LOCAL_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/sw.js',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(LOCAL_ASSETS))
  );
});

self.addEventListener('activate', (event) => {
  // 清理旧缓存 / Clean up old caches
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // 跳过 API 请求，直接走网络 / Bypass SW for API endpoints
  if (url.pathname.startsWith('/api/')) return;
  
  // 仅缓存本地资源，CDN 资源走网络
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
  }
  // Google Fonts / 其他外部资源直接 fetch
});
