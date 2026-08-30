{% load static %}const VERSION = "v13";
const SHELL_CACHE = `pack-directory-shell-${VERSION}`;
const DATA_CACHE = `pack-directory-data-${VERSION}`;
const FONT_CACHE = `pack-directory-fonts-${VERSION}`;
const CURRENT_CACHES = [SHELL_CACHE, DATA_CACHE, FONT_CACHE];

const APP_URL = "{% url 'mobile:index' %}";
const API_PREFIX = APP_URL + "api/";
const MEDIA_PREFIX = "/media/";

// Set by api.js on a photo-warming fetch that needs to know the *real*,
// current bytes before it resolves (a forced "Refresh Data" or the periodic
// re-warm), rather than the cache-first response staleWhileRevalidate()
// normally returns while it revalidates in the background.
const FORCE_REVALIDATE_HEADER = "X-Packman-Force-Revalidate";

// Static assets only. The app shell itself is behind a login and carries the
// signed-in member's name, so it is cached from a real navigation instead (see
// the navigate branch below) rather than fetched blind at install time.
const PRECACHE_URLS = [
  "{% static 'mobile/css/app.css' %}",
  "{% static 'mobile/js/app.js' %}",
  "{% static 'mobile/js/api.js' %}",
  "{% static 'mobile/js/router.js' %}",
  "{% static 'mobile/js/components.js' %}",
  "{% static 'mobile/js/install.js' %}",
  "{% static 'mobile/js/menu.js' %}",
  "{% static 'mobile/js/screens/den-shared.js' %}",
  "{% static 'mobile/js/screens/home.js' %}",
  "{% static 'mobile/js/screens/my-dens.js' %}",
  "{% static 'mobile/js/screens/dens.js' %}",
  "{% static 'mobile/js/screens/search.js' %}",
  "{% static 'mobile/js/screens/profile.js' %}",
  "{% static 'mobile/js/screens/committees.js' %}",
  "{% static 'mobile/icons/icon-192.png' %}",
  "{% static 'mobile/icons/icon-512.png' %}",
  "{% static 'mobile/icons/apple-touch-icon.png' %}",
  "{% static 'mobile/icons/favicon-32.png' %}",
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

/**
 * Everything cached for the signed-in member. `keepShell` spares the precached
 * app shell: "Refresh Data" no longer reloads the page, so a deleted shell
 * would leave the next offline launch with nothing to boot from. Member
 * photos alongside it are pruned rather than wiped wholesale: anything still
 * listed in `keepPhotoPaths` (the current directory's avatars/photos) is left
 * in place — the caller re-fetches those itself so they get revalidated
 * instead of thrown away and re-downloaded from scratch — while photos for
 * members who are no longer in the directory are dropped for good.
 */
async function purgeCaches({ keepShell, keepPhotoPaths = new Set() }) {
  await caches.delete(DATA_CACHE);
  if (!keepShell) {
    await caches.delete(SHELL_CACHE);
    return;
  }
  const cache = await caches.open(SHELL_CACHE);
  const keep = new Set([
    ...[...PRECACHE_URLS, APP_URL].map((url) => new URL(url, self.location.origin).pathname),
    ...keepPhotoPaths,
  ]);
  const cached = await cache.keys();
  await Promise.all(
    cached.filter((request) => !keep.has(new URL(request.url).pathname)).map((request) => cache.delete(request))
  );
}

// The app asks for a full purge when the session ends or a different member
// signs in, so one family's directory is never served to the next; and for a
// data-only purge when the reader taps "Refresh Data" in the Menu, which also
// carries the paths of every photo the fresh directory still references so
// only orphaned ones are dropped. Both flows send a reply port and wait for
// it, so their own requests can't race the purge — except sign-out, which
// doesn't care and leaves event.ports empty.
self.addEventListener("message", (event) => {
  if (event.data === "packman:purge") {
    event.waitUntil(purgeCaches({ keepShell: false }).then(() => event.ports[0]?.postMessage("done")));
    return;
  }
  if (event.data && event.data.type === "packman:purge-data") {
    const keepPhotoPaths = new Set(event.data.keepPhotoPaths || []);
    event.waitUntil(
      purgeCaches({ keepShell: true, keepPhotoPaths }).then(() => event.ports[0]?.postMessage("done"))
    );
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

/**
 * Ask the server whether a cached member photo is still current, using its
 * own ETag/Last-Modified (production's nginx sends both and honors either as
 * a conditional request). A 304 means the cached copy is still good; a fresh
 * 200 replaces it for next time. Runs after the response has already gone
 * out, via event.waitUntil() in staleWhileRevalidate() below, so it never
 * delays what the reader sees.
 */
async function revalidate(request, cacheName, cached) {
  try {
    const headers = new Headers(request.headers);
    const etag = cached.headers.get("ETag");
    const lastModified = cached.headers.get("Last-Modified");
    if (etag) headers.set("If-None-Match", etag);
    if (lastModified) headers.set("If-Modified-Since", lastModified);
    const response = await fetch(request, { headers });
    if (response.status !== 304 && isCacheable(response)) {
      cachePut(cacheName, request, response);
    }
  } catch {
    // Offline or a transient failure — the cached copy stays put.
  }
}

/**
 * Member photos: serve the cached copy immediately (fast, and works
 * offline), then revalidate with the server in the background. This is the
 * only cache-first traffic whose bytes can change without its URL changing
 * (a headshot re-uploaded to the same path) — static assets don't need this,
 * since they're already invalidated by the VERSION bump above.
 */
async function staleWhileRevalidate(event, request, cacheName) {
  const cached = await caches.match(request);
  if (cached) {
    event.waitUntil(revalidate(request, cacheName, cached));
    return cached;
  }
  const response = await fetch(request);
  if (isCacheable(response)) cachePut(cacheName, request, response);
  return response;
}

/**
 * Same conditional-request check as revalidate() above, but awaited instead
 * of run in the background — for the photo-warming pass behind a forced
 * "Refresh Data" (or the periodic re-warm), which needs to know the fresh
 * bytes are actually in the cache before it reports itself done, rather than
 * handing back stale bytes while a background fetch is still in flight.
 */
async function forceRevalidate(request, cacheName) {
  const cached = await caches.match(request);
  try {
    const headers = new Headers(request.headers);
    headers.delete(FORCE_REVALIDATE_HEADER);
    if (cached) {
      const etag = cached.headers.get("ETag");
      const lastModified = cached.headers.get("Last-Modified");
      if (etag) headers.set("If-None-Match", etag);
      if (lastModified) headers.set("If-Modified-Since", lastModified);
    }
    const response = await fetch(request, { headers });
    if (response.status === 304 && cached) return cached;
    if (isCacheable(response)) cachePut(cacheName, request, response);
    return response;
  } catch {
    if (cached) return cached;
    throw new Error("offline and nothing cached yet");
  }
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

  if (url.pathname.startsWith(MEDIA_PREFIX)) {
    if (event.request.headers.has(FORCE_REVALIDATE_HEADER)) {
      // Photo-warming wants to know the fresh bytes actually landed before
      // it moves on, not just that a background revalidation started.
      event.respondWith(forceRevalidate(event.request, SHELL_CACHE));
      return;
    }
    // Member photos: cache-first, but revalidated in the background so a
    // headshot re-uploaded to the same path doesn't get stuck stale forever.
    event.respondWith(staleWhileRevalidate(event, event.request, SHELL_CACHE));
    return;
  }

  // Static assets: cache-first, filling the cache as we go. Invalidated by
  // the VERSION bump above rather than per-request revalidation.
  event.respondWith(cacheFirst(event.request, SHELL_CACHE));
});
