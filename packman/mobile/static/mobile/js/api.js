const BASE = "/mobile/api/";

// Directory responses are cached locally so screens paint from the last known
// data instead of a spinner, and keep working offline. Entries are revalidated
// in the background; a screen that is already mounted re-renders itself when
// the refreshed data differs (see the packman:data-refresh listener in app.js).
const CACHE_PREFIX = "packman:api:v1:";
const CACHE_OWNER_KEY = "packman:api:owner";
const REFRESH_EVENT = "packman:data-refresh";

// How long a cached entry is served without hitting the network at all. Short
// enough that a stale roster corrects itself on the next screen visit, long
// enough that flicking between tabs doesn't refetch everything.
const FRESH_MS = 30_000;

function cacheKey(url) {
  return CACHE_PREFIX + url;
}

function readCache(url) {
  try {
    const raw = localStorage.getItem(cacheKey(url));
    return raw ? JSON.parse(raw) : null;
  } catch {
    // Corrupt entry or storage unavailable (private browsing) — treat as a miss.
    return null;
  }
}

function writeCache(url, data) {
  try {
    localStorage.setItem(cacheKey(url), JSON.stringify({ at: Date.now(), data }));
  } catch {
    // Out of quota or storage blocked: drop what we have and carry on. The app
    // still works, it just goes to the network every time.
    purgeCache();
  }
}

export function purgeCache() {
  try {
    Object.keys(localStorage)
      .filter((key) => key.startsWith(CACHE_PREFIX))
      .forEach((key) => localStorage.removeItem(key));
  } catch {
    // Nothing cached to clear.
  }
  // The service worker holds its own copy of the same responses.
  navigator.serviceWorker?.controller?.postMessage("packman:purge");
}

/**
 * The Menu screen's "Refresh Data" button: clears every cache the PWA keeps
 * — this tab's localStorage cache and the service worker's shell/data caches
 * — then reloads, so the next paint is a genuine network fetch of everything
 * rather than whatever was last stored.
 */
export async function refreshAllData() {
  try {
    Object.keys(localStorage)
      .filter((key) => key.startsWith(CACHE_PREFIX))
      .forEach((key) => localStorage.removeItem(key));
  } catch {
    // Nothing cached to clear.
  }

  const controller = navigator.serviceWorker?.controller;
  if (controller) {
    // Wait for the service worker to confirm its caches are gone before
    // reloading, so the reload's own requests can't race the purge and pull
    // a cached copy right back in. An old service worker that predates this
    // reply won't ever post back, so give up and reload anyway after a beat.
    await new Promise((resolve) => {
      const channel = new MessageChannel();
      channel.port1.onmessage = () => resolve();
      controller.postMessage("packman:purge", [channel.port2]);
      setTimeout(resolve, 1500);
    });
  }

  window.location.reload();
}

/**
 * Cached directory data belongs to whoever was signed in when it was stored.
 * Clear it whenever the shell reports a different member.
 */
export function claimCacheFor(slug) {
  try {
    if (localStorage.getItem(CACHE_OWNER_KEY) !== slug) {
      purgeCache();
      localStorage.setItem(CACHE_OWNER_KEY, slug);
    }
  } catch {
    // Storage blocked; nothing was cached in the first place.
  }
}

function redirectToLogin() {
  // Session is gone: the cached directory is no longer ours to keep.
  purgeCache();
  // Keep the hash-based in-app route so post-login lands back on the same screen.
  const next = encodeURIComponent(
    window.location.pathname + window.location.search + window.location.hash
  );
  window.location.href = `${window.PACKMAN_MOBILE.loginUrl}?next=${next}`;
}

function buildUrl(path, params) {
  const url = new URL(BASE + path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }
  return url;
}

async function fetchJson(url) {
  const response = await fetch(url, { credentials: "same-origin" });

  if (response.status === 401 || response.status === 403) {
    redirectToLogin();
    throw new Error("Not authenticated");
  }
  if (!response.ok) {
    throw new Error(`Request to ${url.pathname} failed: ${response.status}`);
  }
  return response.json();
}

async function request(path, params) {
  return fetchJson(buildUrl(path, params));
}

/**
 * Stale-while-revalidate: resolve from cache when we have it, and refresh in
 * the background. Falls back to whatever is cached when the network fails, so
 * the directory stays readable offline.
 */
async function cachedRequest(path, params) {
  const url = buildUrl(path, params);
  const key = url.toString();
  const cached = readCache(key);

  if (!cached) {
    const fresh = await fetchJson(url);
    writeCache(key, fresh);
    return fresh;
  }

  if (Date.now() - cached.at < FRESH_MS) {
    return cached.data;
  }

  fetchJson(url)
    .then((fresh) => {
      writeCache(key, fresh);
      if (JSON.stringify(fresh) !== JSON.stringify(cached.data)) {
        window.dispatchEvent(new CustomEvent(REFRESH_EVENT, { detail: { key } }));
      }
    })
    .catch(() => {
      // Offline or a transient failure — the cached copy already rendered.
    });

  return cached.data;
}

export const api = {
  home: () => cachedRequest("home/"),
  myDens: () => cachedRequest("dens/mine/"),
  dens: () => cachedRequest("dens/"),
  den: (number) => cachedRequest(`dens/${number}/`),
  // Searches aren't cached: results are query-specific and would fill storage
  // with one entry per keystroke.
  search: (q, type) => request("search/", { q, type }),
  member: (slug) => cachedRequest(`members/${encodeURIComponent(slug)}/`),
  committees: () => cachedRequest("committees/"),
  committee: (slug, year) => cachedRequest(`committees/${encodeURIComponent(slug)}/`, { year }),
};

/**
 * Fill the caches the directory reads from, so the first offline launch after an
 * install doesn't find them empty. Covers the three screens reachable without
 * picking a den or typing a search; the rest fill in as they're visited.
 */
export async function preloadCriticalData() {
  try {
    await Promise.all([api.home(), api.dens(), api.myDens()]);
  } catch (err) {
    // Offline, or the session expired mid-install. Nothing to recover: the
    // screens each cache themselves on the way past.
    console.warn("Pre-load skipped", err);
  }
}
