/* WasteWise AI service worker: cache the app shell, network-first for API calls. */
const CACHE_NAME = "wastewise-ai-v14";
const APP_SHELL = [
  "/",
  "/login.html",
  "/scan.html",
  "/result.html",
  "/create.html",
  "/make.html",
  "/recycle.html",
  "/dispose.html",
  "/dashboard.html",
  "/profile.html",
  "/history.html",
  "/css/styles.css",
  "/js/api.js",
  "/js/auth.js",
  "/js/state.js",
  "/js/nav.js",
  "/js/demo.js",
  "/js/shell.js",
  "/js/camera.js",
  "/js/sw-register.js",
  "/js/home.js",
  "/js/scan.js",
  "/js/result.js",
  "/js/history.js",
  "/js/create.js",
  "/js/make.js",
  "/js/recycle.js",
  "/js/dispose.js",
  "/js/dashboard.js",
  "/js/profile.js",
  "/manifest.json",
  "/assets/icons/icon-192.png",
  "/assets/icons/icon-512.png",
  "/assets/wastewise-logo.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // API: network first, fall back to cache (mostly to avoid hard failures offline).
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          const copy = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return resp;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // App shell / static assets: cache-first with network update.
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request).then((resp) => {
        if (resp && resp.status === 200) {
          const copy = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return resp;
      });
      return cached || network;
    })
  );
});
