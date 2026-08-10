export function esc(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

// Rank colours are defined as CSS custom properties so both the day and night
// palettes can restate them; these are the references the inline styles below
// resolve against.
export const RANK_COLORS = {
  lion: "var(--rank-lion)",
  tiger: "var(--rank-tiger)",
  wolf: "var(--rank-wolf)",
  bear: "var(--rank-bear)",
  webelos: "var(--rank-webelos)",
  aol: "var(--rank-aol)",
};

// The same ranks set as text rather than as a fill. Night mode lifts these
// further than the badge fills, which have to stay dark enough for white text.
const RANK_TEXT_COLORS = {
  lion: "var(--rank-lion-text)",
  tiger: "var(--rank-tiger-text)",
  wolf: "var(--rank-wolf-text)",
  bear: "var(--rank-bear-text)",
  webelos: "var(--rank-webelos-text)",
  aol: "var(--rank-aol-text)",
};

const AVATAR_PALETTE = ["#c0392b", "#1f8a5b", "#5b4bb0", "#2f6fb0", "#e08a1e", "#0f766e"];

export function rankColor(rankKey) {
  return RANK_COLORS[rankKey] || "var(--rank-webelos)";
}

export function rankTextColor(rankKey) {
  return RANK_TEXT_COLORS[rankKey] || "var(--rank-webelos-text)";
}

export function initialsOf(name) {
  return (name || "")
    .split(" ")
    .filter(Boolean)
    .map((word) => word[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function colorFor(name) {
  let hash = 0;
  for (const ch of name || "") {
    hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  }
  return AVATAR_PALETTE[hash % AVATAR_PALETTE.length];
}

export function avatar(url, name, size = "sm") {
  if (url) {
    return `<img class="av ${size}" src="${esc(url)}" alt="${esc(name)}" loading="lazy">`;
  }
  return `<span class="av ${size}" style="background:${colorFor(name)}">${esc(initialsOf(name))}</span>`;
}

export function denBadge(rankKey, badgeText, size = "") {
  return `<span class="den-badge ${size}" style="background:${rankColor(rankKey)}">${esc(badgeText || "?")}</span>`;
}

export function rankTag(rankKey, text) {
  if (!text) return "";
  return `<span class="tag" style="background:${rankColor(rankKey)}">${esc(text)}</span>`;
}

export function pluralize(count, noun) {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

export const icons = {
  home: '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/></svg>',
  myDens:
    '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke-width="2"><circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6"/><path d="M16 5.5a3 3 0 010 5.4M18 14c2.4.6 3.5 2.7 3.5 6"/></svg>',
  dens: '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="3" width="7" height="7" rx="1.6"/><rect x="3" y="14" width="7" height="7" rx="1.6"/><rect x="14" y="14" width="7" height="7" rx="1.6"/></svg>',
  search:
    '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke-width="2"><circle cx="10.5" cy="10.5" r="7"/><path d="M16 16l5 5"/></svg>',
  me: '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke-width="2"><circle cx="12" cy="8" r="3.5"/><path d="M5 20c0-4 3-7 7-7s7 3 7 7"/></svg>',
  phone:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6.6 2.5a1.7 1.7 0 00-1.5.5L3.7 4.9c-.5.5-.7 1.2-.5 1.9 1.9 6.9 6.9 11.9 13.8 13.8.7.2 1.4 0 1.9-.5l1.9-1.4a1.7 1.7 0 00.2-2.4l-2.3-2.6a1.7 1.7 0 00-2-.4l-1.9.9a13 13 0 01-5-5l.9-1.9a1.7 1.7 0 00-.4-2L8 3z"/></svg>',
  message:
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H8l-5 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
  mail: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><rect x="2.5" y="4.5" width="19" height="15" rx="2.5"/><path d="M3 6l9 6 9-6"/></svg>',
  searchGray:
    '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="10.5" cy="10.5" r="7"/><path d="M16 16l5 5"/></svg>',
};

// How many dens the user's cubs span — drives the "My Den" vs "My Dens"
// nav label. Learned from Home/My Dens API data as screens load.
const DEN_COUNT_KEY = "packman:myDenCount";

export function setMyDenCount(count) {
  try {
    sessionStorage.setItem(DEN_COUNT_KEY, String(count));
  } catch {
    // Private browsing may block sessionStorage; the label just stays plural.
  }
  window.dispatchEvent(new CustomEvent("packman:den-count"));
}

export function myDensLabel() {
  try {
    return sessionStorage.getItem(DEN_COUNT_KEY) === "1" ? "My Den" : "My Dens";
  } catch {
    return "My Dens";
  }
}

export function appBar(inner, { column = false } = {}) {
  return `<header class="appbar${column ? " column" : ""}">${inner}</header>`;
}

export function titleBar(title, meta) {
  return appBar(
    `<div class="appbar-title">${esc(title)}</div>${meta ? `<div class="appbar-meta">${esc(meta)}</div>` : ""}`
  );
}
