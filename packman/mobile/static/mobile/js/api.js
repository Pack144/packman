const BASE = "/mobile/api/";

// Directory responses are cached locally so screens paint from the last known
// data instead of a spinner, and keep working offline. Entries are revalidated
// in the background; a screen that is already mounted re-renders itself when
// the refreshed data differs (see the packman:data-refresh listener in app.js).
const CACHE_PREFIX = "packman:api:v1:";
const CACHE_OWNER_KEY = "packman:api:owner";
const PRIMED_AT_KEY = "packman:api:primedAt";
const REFRESH_EVENT = "packman:data-refresh";

// How long a cached entry is served without hitting the network at all. Short
// enough that a stale roster corrects itself on the next screen visit, long
// enough that flicking between tabs doesn't refetch everything.
const FRESH_MS = 30_000;

// How long a full directory pre-load stands before primeAllData() re-fetches
// every endpoint rather than just topping up what's missing. A full pass is
// ~70 requests, so it is not something to repeat on every launch.
const PRIME_TTL_MS = 6 * 60 * 60 * 1000;

// Browsers allow six connections per host on HTTP/1.1; staying just under that
// keeps the pre-load from starving whatever the reader is actively looking at.
const PRIME_CONCURRENCY = 5;

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

// Set when a write runs out of room, so an in-flight pre-load stops instead of
// grinding through another sixty writes that cannot land.
let storageFull = false;

// The Search screen's view of the cache (see peopleIndex), rebuilt lazily and
// dropped whenever anything underneath it is written.
let peopleCache = null;

function writeCache(url, data) {
  try {
    localStorage.setItem(cacheKey(url), JSON.stringify({ at: Date.now(), data }));
    peopleCache = null;
  } catch {
    // Out of quota or storage blocked. Drop only what wouldn't fit: a pre-load
    // that overflows near the end should keep the sixty profiles it already
    // stored rather than emptying the directory over the last one.
    storageFull = true;
  }
}

export function purgeCache() {
  try {
    Object.keys(localStorage)
      .filter((key) => key.startsWith(CACHE_PREFIX))
      .forEach((key) => localStorage.removeItem(key));
    localStorage.removeItem(PRIMED_AT_KEY);
  } catch {
    // Nothing cached to clear.
  }
  peopleCache = null;
  // The service worker holds its own copy of the same responses.
  navigator.serviceWorker?.controller?.postMessage("packman:purge");
}

/**
 * Ask the service worker to drop its cached API responses and member photos,
 * keeping the precached app shell. Resolves once it confirms.
 */
function purgeServiceWorkerData() {
  const controller = navigator.serviceWorker?.controller;
  if (!controller) return Promise.resolve();
  // Wait for the confirmation so a repaint can't race the purge and pull a
  // stale avatar straight back in. A service worker predating this message
  // won't ever reply, so give up and carry on after a beat.
  return new Promise((resolve) => {
    const channel = new MessageChannel();
    channel.port1.onmessage = () => resolve();
    controller.postMessage("packman:purge-data", [channel.port2]);
    setTimeout(resolve, 1500);
  });
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
  // with one entry per keystroke. The Search screen matches the cached
  // directory itself (see searchLocal) and only falls back to this.
  search: (q, type) => request("search/", { q, type }),
  member: (slug) => cachedRequest(`members/${encodeURIComponent(slug)}/`),
  committees: () => cachedRequest("committees/"),
  committee: (slug, year) => cachedRequest(`committees/${encodeURIComponent(slug)}/`, { year }),
};

/* ------------------------------------------------------------------ *
 * Pre-loading the whole directory
 * ------------------------------------------------------------------ */

function primedAt() {
  try {
    return Number(localStorage.getItem(PRIMED_AT_KEY)) || 0;
  } catch {
    return 0;
  }
}

/** Work through `tasks` a few at a time, giving up if the connection drops. */
async function drain(tasks, onSettled) {
  let next = 0;
  const worker = async () => {
    while (next < tasks.length && !storageFull && navigator.onLine !== false) {
      const task = tasks[next++];
      try {
        await task();
      } catch {
        // One member out of visibility scope, or a blip. The rest still stand.
      }
      onSettled?.();
    }
  };
  await Promise.all(Array.from({ length: Math.min(PRIME_CONCURRENCY, tasks.length) }, worker));
}

let priming = null;
let primingForced = false;
let waitingForOnline = false;

function retryWhenOnline() {
  if (waitingForOnline) return;
  waitingForOnline = true;
  window.addEventListener(
    "online",
    () => {
      waitingForOnline = false;
      primeAllData();
    },
    { once: true }
  );
}

function denSlugs(den) {
  const slugs = (den.leaders || []).map((leader) => leader.slug);
  (den.roster || []).forEach((entry) => {
    if (entry.scout?.slug) slugs.push(entry.scout.slug);
    (entry.parents || []).forEach((parent) => slugs.push(parent.slug));
  });
  return slugs;
}

function committeeSlugs(committee) {
  return [...(committee.akelas || []), ...(committee.members || [])].map((member) => member.slug);
}

async function runPrime({ force, onProgress }) {
  if (navigator.onLine === false) {
    retryWhenOnline();
    return false;
  }

  storageFull = false;
  let changed = false;
  let done = 0;
  let total = 0;
  const settled = () => onProgress?.(++done, total);

  // Past the TTL (or on a manual refresh) every endpoint is re-fetched;
  // otherwise this pass only fills in what isn't cached yet.
  const refetch = force || Date.now() - primedAt() > PRIME_TTL_MS;

  async function load(path, params, { revalidate = false } = {}) {
    const url = buildUrl(path, params);
    const key = url.toString();
    const cached = readCache(key);

    if (cached && !force) {
      // Still inside the freshness window, which on a cold launch means the
      // screen that just painted fetched this a moment ago. Don't ask twice.
      if (Date.now() - cached.at < FRESH_MS) return cached.data;
      if (!revalidate && !refetch) return cached.data;
    }

    const fresh = await fetchJson(url);
    if (cached && JSON.stringify(cached.data) !== JSON.stringify(fresh)) changed = true;
    writeCache(key, fresh);
    return fresh;
  }

  // The index endpoints, always revalidated — they back the four tab screens,
  // so they're the ones worth a round trip on every launch. The first doubles
  // as the reachability probe: navigator.onLine only reports that the radio is
  // on, and there's no point firing seventy more requests at a captive portal.
  let home;
  let dens;
  let myDens;
  let committees;
  try {
    home = await load("home/", undefined, { revalidate: true });
    [dens, myDens, committees] = await Promise.all([
      load("dens/", undefined, { revalidate: true }),
      load("dens/mine/", undefined, { revalidate: true }),
      load("committees/", undefined, { revalidate: true }),
    ]);
  } catch {
    retryWhenOnline();
    return false;
  }
  done = 4;

  // Every den and committee in full, which is also how the member list is
  // discovered: there is no endpoint that enumerates members, but a profile
  // link only ever originates from a den roster, a committee roster or the
  // Home family card — so their union is exactly the set of profiles that can
  // be reached by tapping through the app.
  const denNumbers = (dens.dens || []).map((den) => den.number);
  const committeeList = (committees.committees || []).map((committee) => committee.slug);

  const myDenNumbers = new Set((myDens.dens || []).map((den) => den.number));
  const mine = new Set();
  (home.family?.adults || []).forEach((adult) => mine.add(adult.slug));
  (home.family?.children || []).forEach((child) => mine.add(child.slug));
  (myDens.dens || []).forEach((den) => denSlugs(den).forEach((slug) => mine.add(slug)));

  const nearby = new Set();
  const rest = new Set();

  total = 4 + denNumbers.length + committeeList.length;
  await drain(
    [
      ...denNumbers.map((number) => async () => {
        const den = await load(`dens/${number}/`);
        const into = myDenNumbers.has(number) ? nearby : rest;
        denSlugs(den).forEach((slug) => into.add(slug));
      }),
      ...committeeList.map((slug) => async () => {
        const committee = await load(`committees/${encodeURIComponent(slug)}/`);
        committeeSlugs(committee).forEach((member) => rest.add(member));
      }),
    ],
    settled
  );

  // Own family first, then the rosters of the reader's own dens, then everyone
  // else — so the profiles most likely to be tapped are cached soonest.
  const slugs = [...mine, ...nearby, ...rest].filter(
    (slug, index, all) => slug && all.indexOf(slug) === index
  );

  total = done + slugs.length;
  await drain(
    slugs.map((slug) => async () => {
      await load(`members/${encodeURIComponent(slug)}/`);
    }),
    settled
  );

  if (storageFull) {
    console.warn("Directory pre-load stopped early: local storage is full");
  } else if (navigator.onLine !== false) {
    try {
      localStorage.setItem(PRIMED_AT_KEY, String(Date.now()));
    } catch {
      // Storage blocked; the next launch simply primes again.
    }
  }

  // One event for the whole pass rather than one per endpoint, so the mounted
  // screen repaints once instead of seventy times. A forced pass stays quiet:
  // refreshAllData() announces itself once it has purged the photo cache too,
  // and two events back to back would repaint the screen twice.
  if (changed && !force) {
    window.dispatchEvent(new CustomEvent(REFRESH_EVENT, { detail: { key: null } }));
  }
  return true;
}

/**
 * Fetch and cache the entire directory — every den, committee and member
 * profile reachable in the app — so it all works offline. Runs in the
 * background; screens read what it stores through the normal cache.
 *
 * Concurrent calls share the one pass. Resolves false when there was nothing
 * to talk to, in which case it retries once the connection comes back.
 */
export function primeAllData({ force = false, onProgress } = {}) {
  // A forced pass can't just join a background one already in flight — that
  // one is topping up gaps, not re-fetching, and "Refresh Data" would report
  // success without having asked the server anything.
  if (priming && (!force || primingForced)) return priming;

  const inFlight = priming;
  primingForced = force;
  priming = (async () => {
    // Let the background pass finish rather than running two fan-outs at once.
    if (inFlight) await inFlight.catch(() => {});
    return runPrime({ force, onProgress });
  })().finally(() => {
    priming = null;
    primingForced = false;
  });
  return priming;
}

/**
 * The Menu screen's "Refresh Data" button: re-fetch the whole directory, then
 * swap it in. The fetch comes first on purpose — purging up front would leave
 * a reader who tapped this offline with an empty app and no way to refill it.
 */
export async function refreshAllData(onProgress) {
  if (navigator.onLine === false) return false;

  const refreshed = await primeAllData({ force: true, onProgress });
  if (!refreshed) return false;

  // Avatars and profile photos are served cache-first, so they'd stay stale
  // otherwise. Only the shell survives, since nothing is reloading to refill it.
  await purgeServiceWorkerData();
  window.dispatchEvent(new CustomEvent(REFRESH_EVENT, { detail: { key: null } }));
  return true;
}

/* ------------------------------------------------------------------ *
 * Searching the cached directory
 * ------------------------------------------------------------------ */

function eachCached(visit) {
  try {
    Object.keys(localStorage).forEach((key) => {
      if (!key.startsWith(CACHE_PREFIX)) return;
      try {
        const entry = JSON.parse(localStorage.getItem(key));
        if (entry?.data) visit(key.slice(CACHE_PREFIX.length), entry.data);
      } catch {
        // Corrupt entry; skip it.
      }
    });
  } catch {
    // Storage unavailable.
  }
}

function searchRow(member, extra) {
  // The server labels a parent by who they're a parent of. The same names are
  // on the profile as `Cub · Den 4 · Wolves` relations, and a full name always
  // starts with the short name the server uses, so the first word matches.
  const cubs = (member.family || [])
    .filter((relation) => (relation.relation || "").startsWith("Cub"))
    .map((relation) => (relation.name || "").split(" ")[0]);

  return {
    slug: member.slug,
    name: member.name,
    type: member.is_scout ? "cub" : "parent",
    subtitle: member.is_scout
      ? member.den || ""
      : cubs.length
        ? `Parent of ${cubs.join(", ")}`
        : extra.role || "",
    avatar: member.avatar,
    rank: member.rank,
    rank_key: member.rank_key,
    rank_badge: extra.rank_badge || null,
  };
}

/**
 * Every cached profile, in the shape the Search screen renders. Built by
 * merging the two cached shapes that describe a person: the member detail
 * carries the full name, and the den roster carries a cub's rank badge and an
 * adult's role, neither of which the profile endpoint returns.
 */
export function peopleIndex() {
  if (peopleCache) return peopleCache;

  const extras = new Map();
  eachCached((path, data) => {
    if (!/\/api\/dens\/\d+\/$/.test(path)) return;
    (data.roster || []).forEach((entry) => {
      if (entry.scout?.slug) extras.set(entry.scout.slug, { rank_badge: entry.scout.rank_badge });
      (entry.parents || []).forEach((parent) => extras.set(parent.slug, { role: parent.role }));
    });
  });

  const people = new Map();
  eachCached((path, data) => {
    if (!/\/api\/members\/[^/]+\/$/.test(path) || !data.slug) return;
    people.set(data.slug, searchRow(data, extras.get(data.slug) || {}));
  });

  peopleCache = [...people.values()].sort((a, b) => a.name.localeCompare(b.name));
  return peopleCache;
}

/**
 * Match the cached directory by name. Instant and works offline, but it only
 * sees the display names the API returns — `nickname or first_name` plus the
 * last name — so a middle name, or the legal first name of somebody who goes
 * by a nickname, finds nothing here. The Search screen asks the server when
 * this comes back empty.
 */
export function searchLocal(query, type = "all") {
  const needle = query.trim().toLowerCase();
  if (!needle) return { cubs: [], parents: [] };

  const hits = peopleIndex().filter((person) => person.name.toLowerCase().includes(needle));
  return {
    cubs: type === "parent" ? [] : hits.filter((person) => person.type === "cub"),
    parents: type === "cub" ? [] : hits.filter((person) => person.type === "parent"),
  };
}
