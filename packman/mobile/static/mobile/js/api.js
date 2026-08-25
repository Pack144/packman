const BASE = "/mobile/api/";

// The directory + event responses are cached locally so screens paint from
// the last known data instead of a spinner, and keep working offline. Entries
// are revalidated in the background; a screen that is already mounted
// re-renders itself when the refreshed data differs (see the
// packman:data-refresh listener in app.js).
const CACHE_PREFIX = "packman:api:v3:";
const CACHE_OWNER_KEY = "packman:api:owner";
const PRIMED_AT_KEY = "packman:api:primedAt";
const REFRESH_EVENT = "packman:data-refresh";

// How long a cached entry is served without hitting the network at all. Short
// enough that a stale roster corrects itself on the next screen visit, long
// enough that flicking between tabs doesn't refetch everything.
const FRESH_MS = 30_000;

// How long a directory pre-load stands before primeAllData() re-warms every
// member's photo rather than trusting what's already stored.
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
// grinding through another round of image fetches that cannot land.
let storageFull = false;

// getDirectory()'s built view of the last directory payload seen, keyed off
// that payload's own JSON so it's cheap to tell whether a revalidated fetch
// actually changed anything worth rebuilding for.
let directorySourceJSON = null;
let directoryView = null;

function writeCache(url, data) {
  try {
    localStorage.setItem(cacheKey(url), JSON.stringify({ at: Date.now(), data }));
  } catch {
    // Out of quota or storage blocked.
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
  directorySourceJSON = null;
  directoryView = null;
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

function buildUrl(path) {
  return new URL(BASE + path, window.location.origin);
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

/**
 * Stale-while-revalidate: resolve from cache when we have it, and refresh in
 * the background. Falls back to whatever is cached when the network fails, so
 * the directory stays readable offline.
 */
async function cachedRequest(path) {
  const url = buildUrl(path);
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

// The mobile PWA's only two network calls: the whole member/den/committee
// directory (see getDirectory() below for the shape screens actually read),
// and the next upcoming event, which is cached separately because its
// freshness matters on its own schedule.
export const api = {
  directory: () => cachedRequest("pack_directory/"),
  event: () => cachedRequest("event/"),
};

/* ------------------------------------------------------------------ *
 * Turning the raw directory payload into something screens can read
 * without re-deriving the same lookups over and over.
 * ------------------------------------------------------------------ */

/** A committee membership reference, resolved against `bySlug` when linked. */
function resolveRef(bySlug, ref) {
  const member = ref.linked ? bySlug.get(ref.slug) : null;
  return {
    slug: ref.slug,
    name: member ? member.name : ref.name,
    avatar: member ? member.avatar : null,
    phone: member?.phone_numbers[0]?.value ?? null,
    email: member?.emails[0] ?? null,
    linked: ref.linked,
  };
}

/**
 * A den leader reference, resolved against `bySlug`. Unlike a committee
 * membership row, a den leader is assumed to always be a linked, visible
 * member — there's no `linked` flag to check; a lookup miss is a data bug
 * to fix, not something this needs to render around.
 */
function resolveLeader(bySlug, leader) {
  const member = bySlug.get(leader.slug);
  return {
    slug: leader.slug,
    name: member ? member.name : leader.name,
    avatar: member?.avatar ?? null,
    position: leader.position,
    phone: member?.phone_numbers[0]?.value ?? null,
    email: member?.emails[0] ?? null,
  };
}

/**
 * Rank/grade for a scout aren't sent per-member — they always match the den
 * `member.den_number` points to (`dens[].rank`/`rank_plural`/`rank_key`/
 * `rank_badge`/`grade`), so resolve them here once and attach them to the
 * member record every other helper below already expects them on.
 */
function denRankFields(den) {
  return {
    rank: den?.rank ?? null,
    rank_plural: den?.rank_plural ?? null,
    rank_key: den?.rank_key ?? null,
    rank_badge: den?.rank_badge ?? null,
    grade: den?.grade ?? null,
  };
}

function buildDirectory(raw) {
  const denRankByNumber = new Map(raw.dens.map((den) => [den.number, den]));
  const members = raw.members.map((member) => ({
    ...member,
    ...denRankFields(member.is_scout ? denRankByNumber.get(member.den_number) : null),
  }));

  const bySlug = new Map(members.map((member) => [member.slug, member]));

  const byFamily = new Map();
  members.forEach((member) => {
    if (!member.family_slug) return;
    if (!byFamily.has(member.family_slug)) byFamily.set(member.family_slug, []);
    byFamily.get(member.family_slug).push(member);
  });

  const dens = raw.dens.map((den) => ({
    ...den,
    leaders: den.leaders.map((leader) => resolveLeader(bySlug, leader)),
    // Every den member is guaranteed to be in `members` (dens only ever show
    // the current year), so a missing lookup just drops that slug quietly.
    roster: den.roster.map((slug) => bySlug.get(slug)).filter(Boolean),
  }));

  const committees = raw.committees.map((committee) => ({
    ...committee,
    // Keyed by year, then by position (e.g. "Chair", "Den Leader") — a flat,
    // server-ordered roster per position (lowest Position value, i.e. most
    // senior, first; then by name); no leadership/rank-and-file split to
    // re-flatten here.
    membership: Object.fromEntries(
      Object.entries(committee.membership).map(([year, byPosition]) => [
        year,
        Object.fromEntries(
          Object.entries(byPosition).map(([position, entries]) => [
            position,
            entries.map((ref) => resolveRef(bySlug, ref)),
          ])
        ),
      ])
    ),
  }));

  return {
    viewerSlug: raw.viewer,
    currentYear: raw.current_year,
    akelaSlug: raw.akela,
    pack: raw.pack,
    me: bySlug.get(raw.viewer) || null,
    bySlug,
    byFamily,
    dens,
    committees,
  };
}

/**
 * Fetch (or read from cache) the single directory call and hand back the
 * frontend-friendly structure every screen reads from — a viewer pointer,
 * member/den/committee lookups already resolved by slug, and no further
 * network activity. Cheap to call repeatedly: the transform only reruns when
 * the underlying payload has actually changed.
 */
export async function getDirectory() {
  const raw = await api.directory();
  const json = JSON.stringify(raw);
  if (json !== directorySourceJSON) {
    directorySourceJSON = json;
    directoryView = buildDirectory(raw);
  }
  return directoryView;
}

/* ------------------------------------------------------------------ *
 * Pre-loading member photos
 * ------------------------------------------------------------------ */

function primedAt() {
  try {
    return Number(localStorage.getItem(PRIMED_AT_KEY)) || 0;
  } catch {
    return 0;
  }
}

/**
 * Ask for an image so the service worker's cache-first handler (see sw.js)
 * stores it, without caring about the response itself — nothing here reads
 * the bytes or the pixels. A missing photo or an offline blip just means
 * that one member's photo isn't warmed yet; the rest of the pre-load
 * shouldn't stop for it.
 */
function warmImage(url) {
  if (!url) return Promise.resolve();
  return fetch(url, { credentials: "same-origin" }).catch(() => {});
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
        // A missing photo or a blip. The rest still stand.
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

async function runPrime({ force, onProgress }) {
  if (navigator.onLine === false) {
    retryWhenOnline();
    return false;
  }

  storageFull = false;
  let changed = false;

  async function load(path) {
    const url = buildUrl(path);
    const key = url.toString();
    const cached = readCache(key);
    const fresh = await fetchJson(url);
    if (cached && JSON.stringify(cached.data) !== JSON.stringify(fresh)) changed = true;
    writeCache(key, fresh);
    return fresh;
  }

  // Both endpoints, always revalidated on launch — this is the entire
  // network fan-out now: no more crawling every den/committee roster to
  // discover member slugs before fetching each profile individually.
  let raw;
  try {
    [raw] = await Promise.all([load("pack_directory/"), load("event/")]);
  } catch {
    retryWhenOnline();
    return false;
  }

  // Past the TTL (or on a manual refresh), every member's photo is re-warmed;
  // otherwise a fresh directory fetch above is already enough for this launch.
  const refetch = force || Date.now() - primedAt() > PRIME_TTL_MS;
  if (refetch) {
    const members = raw.members || [];
    let done = 0;
    onProgress?.(done, members.length);
    await drain(
      members.map((member) => async () => {
        await Promise.all([warmImage(member.avatar), warmImage(member.photo)]);
      }),
      () => onProgress?.(++done, members.length)
    );
  }

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
  // screen repaints once instead of twice. A forced pass stays quiet:
  // refreshAllData() announces itself once it has purged the photo cache too,
  // and two events back to back would repaint the screen twice.
  if (changed && !force) {
    window.dispatchEvent(new CustomEvent(REFRESH_EVENT, { detail: { key: null } }));
  }
  return true;
}

/**
 * Fetch and cache the directory and next event, and warm every member's
 * avatar/profile photo so the whole app works offline. Runs in the
 * background; screens read what it stores through the normal cache.
 *
 * Concurrent calls share the one pass. Resolves false when there was nothing
 * to talk to, in which case it retries once the connection comes back.
 */
export function primeAllData({ force = false, onProgress } = {}) {
  // A forced pass can't just join a background one already in flight — that
  // one may skip re-warming photos, and "Refresh Data" would report success
  // without having actually refreshed them.
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
 * The Menu screen's "Refresh Data" button: re-fetch the directory and event,
 * then swap them in. The fetch comes first on purpose — purging up front
 * would leave a reader who tapped this offline with an empty app and no way
 * to refill it.
 */
export async function refreshAllData(onProgress) {
  if (navigator.onLine === false) return false;

  const refreshed = await primeAllData({ force: true, onProgress });
  if (!refreshed) return false;

  // Avatars and profile photos are served cache-first, so they'd stay stale
  // otherwise. Only the shell survives, since nothing is reloading to refill it.
  await purgeServiceWorkerData();
  await warmAllImages(onProgress);
  window.dispatchEvent(new CustomEvent(REFRESH_EVENT, { detail: { key: null } }));
  return true;
}

/**
 * Re-fetch every cached member's avatar and profile photo. runPrime() already
 * warms them once per pass, but refreshAllData() purges that same image
 * cache right after — a changed headshot has to be able to replace what was
 * there — so it calls this afterwards to put the (now current) photos back
 * before it hands off.
 */
async function warmAllImages(onProgress) {
  const raw = readCache(buildUrl("pack_directory/").toString())?.data;
  const members = raw?.members || [];
  let done = 0;
  await drain(
    members.map((member) => () => Promise.all([warmImage(member.avatar), warmImage(member.photo)])),
    () => onProgress?.(++done, members.length)
  );
}

/* ------------------------------------------------------------------ *
 * Deriving screen-specific views from the cached directory
 * ------------------------------------------------------------------ */

/** "Den 4 · Wolves" — falls back to just "Den 4" if the cub has no rank yet. */
export function denLabel(member) {
  if (member.den_number == null) return null;
  return member.rank_plural ? `Den ${member.den_number} · ${member.rank_plural}` : `Den ${member.den_number}`;
}

function relationLabel(viewer, other) {
  if (other.is_scout) {
    const label = denLabel(other);
    const relation = viewer.is_scout ? "Sibling" : "Cub";
    const withDen = label ? `${relation} · ${label}` : relation;
    return other.active ? withDen : `${withDen} · No longer active`;
  }
  return other.role || "Parent";
}

/**
 * Every other member of `member`'s family, in profile-card order — mirrors
 * the pre-single-call API's build_member_detail() family listing, just
 * computed from the cached directory instead of a per-profile request.
 */
export function familyOf(directory, member) {
  if (!member.family_slug) return [];
  return (directory.byFamily.get(member.family_slug) || [])
    .filter((other) => other.slug !== member.slug)
    .map((other) => ({
      slug: other.slug,
      name: other.name,
      avatar: other.avatar,
      relation: relationLabel(member, other),
      rank: other.rank,
      rank_key: other.rank_key,
      active: other.active,
    }));
}

function lastNameOf(fullName) {
  const parts = (fullName || "").trim().split(/\s+/);
  return parts[parts.length - 1] || "";
}

/** The viewer's own active cubs — the family the Home screen cares about. */
export function myActiveChildren(directory) {
  const me = directory.me;
  if (!me?.family_slug) return [];
  return (directory.byFamily.get(me.family_slug) || []).filter((m) => m.is_scout && m.active);
}

/** Home screen's family card: the viewer's own household. */
export function myFamilyCard(directory) {
  const me = directory.me;
  if (!me?.family_slug) return null;
  const family = directory.byFamily.get(me.family_slug) || [];
  const children = myActiveChildren(directory);
  const lastNames = [...new Set(family.map((m) => lastNameOf(m.name)).filter(Boolean))];
  const name = lastNames.length <= 1 ? `The ${lastNames[0] || ""} Family`.trim() : lastNames.join(" & ");
  return {
    name,
    children: children.map((child) => ({
      slug: child.slug,
      name: child.short_name,
      avatar: child.avatar,
      den_number: child.den_number,
      den_label: denLabel(child) || "",
    })),
    dens: [...new Set(children.map((child) => child.rank_plural).filter(Boolean))],
  };
}

/**
 * The Pack's current Akela, for the Home screen's Jump To card.
 *
 * The Akela is assumed to always be a linked/visible member — a Pack that
 * ever named someone outside the directory as Akela has a data problem to
 * fix on its own, not something this needs to paper over — so this is a
 * single O(1) `bySlug` lookup, not a scan through committee membership rows.
 */
export function currentAkela(directory) {
  if (!directory.akelaSlug) return null;
  const member = directory.bySlug.get(directory.akelaSlug);
  if (!member) return null;
  return { slug: member.slug, name: member.name, avatar: member.avatar, title: "Akela" };
}

/** Den number -> the viewer's own cub assigned there, for "My Dens". */
function myCubByDenNumber(directory) {
  const map = new Map();
  myActiveChildren(directory).forEach((child) => {
    if (child.den_number != null) map.set(child.den_number, child);
  });
  return map;
}

/** A den, with its leaders/roster resolved to full member records. */
function resolveDen(directory, den) {
  const roster = den.roster.map((scout) => ({
    scout: {
      slug: scout.slug,
      name: scout.short_name,
      avatar: scout.avatar,
      rank: scout.rank,
      rank_key: scout.rank_key,
    },
    parents: (scout.family_slug ? directory.byFamily.get(scout.family_slug) || [] : [])
      .filter((m) => !m.is_scout)
      .map((adult) => ({ slug: adult.slug, name: adult.short_name })),
  }));
  return {
    number: den.number,
    rank: den.rank,
    rank_plural: den.rank_plural,
    rank_key: den.rank_key,
    rank_badge: den.rank_badge,
    grade: den.grade,
    leaders: den.leaders,
    roster,
    cub_count: roster.length,
  };
}

/** Every den, resolved and flagged with whether one of the viewer's own cubs is in it. */
export function allDens(directory) {
  const myDenByNumber = myCubByDenNumber(directory);
  return directory.dens.map((den) => {
    const resolved = resolveDen(directory, den);
    const myCub = myDenByNumber.get(den.number);
    return { ...resolved, is_mine: Boolean(myCub), my_cub: myCub ? myCub.short_name : null };
  });
}

/** Just the dens holding one of the viewer's own cubs, for "My Dens". */
export function myDens(directory) {
  const myDenByNumber = myCubByDenNumber(directory);
  return allDens(directory).filter((den) => myDenByNumber.has(den.number));
}

/** A single den by number, resolved — for the Den Detail screen. */
export function denByNumber(directory, number) {
  const den = directory.dens.find((d) => d.number === Number(number));
  return den ? resolveDen(directory, den) : null;
}

/**
 * A Pack Year always runs from the fall of `<year - 1>` through the summer
 * of `<year>`, so the label is derivable from the year alone — the server
 * doesn't need to send it.
 */
export function packYearLabel(year) {
  return `${year - 1}-${year}`;
}

/** A committee's roster for one Pack Year (the most recent one if omitted). */
export function committeeYear(committee, year) {
  const years = committee.years;
  const chosenYear = year ?? years[0] ?? null;
  const byPosition = committee.membership[String(chosenYear)] || {};
  return {
    ...committee,
    year: chosenYear,
    year_label: chosenYear ? packYearLabel(chosenYear) : "",
    // Positions are already server-ordered (most senior first); flattening
    // Object.values() preserves that order across positions.
    members: Object.values(byPosition).flat(),
  };
}

/* ------------------------------------------------------------------ *
 * Searching the cached directory
 * ------------------------------------------------------------------ */

function myFamilyChildNames(directory, adult) {
  if (!adult.family_slug) return [];
  return (directory.byFamily.get(adult.family_slug) || [])
    .filter((m) => m.is_scout && m.active)
    .map((m) => m.short_name);
}

function searchRow(directory, member) {
  let subtitle;
  if (member.is_scout) {
    subtitle = denLabel(member) || "";
  } else {
    const cubs = myFamilyChildNames(directory, member);
    subtitle = cubs.length ? `Parent of ${cubs.join(", ")}` : member.role || "";
  }
  return {
    slug: member.slug,
    name: member.name,
    type: member.is_scout ? "cub" : "parent",
    subtitle,
    avatar: member.avatar,
    rank: member.rank,
    rank_key: member.rank_key,
  };
}

/** Every linkable profile in the cached directory, sorted by display name. */
export function peopleIndex(directory) {
  return [...directory.bySlug.values()]
    .filter((member) => member.linkable)
    .map((member) => searchRow(directory, member))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Match the cached directory by name. Instant and works offline. Only sees
 * the display name (`nickname or first_name` plus the last name), so a
 * middle name or someone's legal first name finds nothing here — there's no
 * server fallback anymore, since there's no per-query endpoint left to ask.
 */
export function searchLocal(directory, query, type = "all") {
  const needle = query.trim().toLowerCase();
  if (!needle) return { cubs: [], parents: [] };

  const hits = peopleIndex(directory).filter((person) => person.name.toLowerCase().includes(needle));
  return {
    cubs: type === "parent" ? [] : hits.filter((person) => person.type === "cub"),
    parents: type === "cub" ? [] : hits.filter((person) => person.type === "parent"),
  };
}
