{% load static %}const VERSION = "v4";
const SHELL_CACHE = `pack-directory-shell-${VERSION}`;
const DATA_CACHE = `pack-directory-data-${VERSION}`;
const FONT_CACHE = `pack-directory-fonts-${VERSION}`;
const CURRENT_CACHES = [SHELL_CACHE, DATA_CACHE, FONT_CACHE];

const APP_URL = "{% url 'mobile:index' %}";
const API_PREFIX = APP_URL + "api/";

// Static assets only. The app shell itself is behind a login and carries the
// signed-in member's name, so it is cached from a real navigation instead (see
// the navigate branch below) rather than fetched blind at install time.
const PRECACHE_URLS = [
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

const FONT_HOSTS = ["fonts.googleapis.com", "fonts.gstatic.com"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) =>
        // Cached one at a time: cache.addAll() rejects as a unit, so a single
        // stale or missing URL would leave the app with no cache at all.
        Promise.all(
          PRECACHE_URLS.map((url) =>
            cache.add(url).catch((err) => console.warn("Precache skipped", url, err))
          )
        )
      )
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => !CURRENT_CACHES.includes(key)).map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  );
});

// The app asks for a purge when the session ends or a different member signs
// in, so one family's directory is never served to the next.
self.addEventListener("message", (event) => {
  if (event.data === "packman:purge") {
    event.waitUntil(Promise.all([caches.delete(DATA_CACHE), caches.delete(SHELL_CACHE)]));
  }
});

/** Only basic, complete 200s are worth storing; redirects can't be cached at all. */
function isCacheable(response) {
  return response && response.ok && !response.redirected && response.type === "basic";
}

function cachePut(cacheName, request, response) {
  const copy = response.clone();
  caches.open(cacheName).then((cache) => cache.put(request, copy));
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (isCacheable(response)) cachePut(cacheName, request, response);
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw err;
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok && (isCacheable(response) || cacheName === FONT_CACHE)) {
    cachePut(cacheName, request, response);
  }
  return response;
}

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);

  // Google Fonts: cache on first use so the Pack's typefaces survive offline.
  if (FONT_HOSTS.includes(url.hostname)) {
    event.respondWith(cacheFirst(event.request, FONT_CACHE));
    return;
  }

  if (url.origin !== self.location.origin) {
    return;
  }

  // The shell: always prefer the network so a signed-out or expired session
  // gets its login redirect, and fall back to the last good copy when offline.
  if (event.request.mode === "navigate") {
    event.respondWith(
      networkFirst(event.request, SHELL_CACHE).catch(() => caches.match(APP_URL))
    );
    return;
  }

  if (url.pathname.startsWith(API_PREFIX)) {
    // Network-first so the directory stays current; fall back to the last
    // known-good response when offline.
    event.respondWith(networkFirst(event.request, DATA_CACHE));
    return;
  }

  // Static assets and member photos: cache-first, filling the cache as we go.
  event.respondWith(cacheFirst(event.request, SHELL_CACHE));
});
