// ScamPulse service worker: offline app shell + cached model/static.
const CACHE = "scampulse-v1";
const SHELL = [
  "/", "/manifest.webmanifest",
  "/static/css/app.css",
  "/static/js/app.js", "/static/js/inference.js",
  "/static/js/normalise.js", "/static/js/strings.js",
  "/static/model.json",
  "/static/icons/icon-192.png", "/static/icons/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;                 // reports/votes go straight to network

  // API: network first, no offline cache (app keeps its own last-good copy)
  if (url.pathname.startsWith("/api/")) {
    e.respondWith(fetch(e.request).catch(() => new Response("{}", { status: 503 })));
    return;
  }
  // navigations: serve the app shell when offline
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).catch(() => caches.match("/")));
    return;
  }
  // everything else (static, fonts): cache-first, then fill the cache
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
    const copy = res.clone();
    if (res.ok) caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
    return res;
  }).catch(() => hit)));
});
