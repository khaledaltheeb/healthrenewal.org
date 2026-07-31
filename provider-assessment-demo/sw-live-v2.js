"use strict";

const RELEASE = "2026.07.24-live.7";
const CACHE = `provider-assessment-${RELEASE}`;
const SCOPE_PATH = "/provider-assessment-demo/";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter((name) => /pterminology|provider-assessment|pa-demo/i.test(name) && name !== CACHE).map((name) => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || !url.pathname.startsWith(SCOPE_PATH)) return;

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(request, { cache: "no-store" });
      if (response.ok) await cache.put(request, response.clone());
      return response;
    } catch (error) {
      const cached = await cache.match(request);
      if (cached) return cached;
      if (request.mode === "navigate") {
        const fallback = await cache.match(new Request(`${self.location.origin}${SCOPE_PATH}?release=${RELEASE}`));
        if (fallback) return fallback;
      }
      throw error;
    }
  })());
});