{% load static %}const CACHE_NAME = "pack-directory-shell-v1";

const PRECACHE_URLS = [
  "{% url 'mobile:index' %}",
  "{% static 'mobile/css/app.css' %}",
  "{% static 'mobile/js/app.js' %}",
  "{% static 'mobile/js/api.js' %}",
  "{% static 'mobile/js/router.js' %}",
  "{% static 'mobile/js/components.js' %}",
  "{% static 'mobile/js/screens/den-shared.js' %}",
  "{% static 'mobile/js/screens/home.js' %}",
  "{% static 'mobile/js/screens/my-dens.js' %}",
  "{% static 'mobile/js/screens/dens.js' %}",
  "{% static 'mobile/js/screens/search.js' %}",
  "{% static 'mobile/js/screens/profile.js' %}",
  "{% static 'mobile/icons/icon-192.png' %}",
  "{% static 'mobile/icons/icon-512.png' %}",
];

const API_PREFIX = "{% url 'mobile:index' %}api/";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);

  if (url.pathname.startsWith(API_PREFIX)) {
    // Network-first so the directory stays current; fall back to the last
    // known-good response when offline.
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

  // Cache-first for the app shell itself.
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
