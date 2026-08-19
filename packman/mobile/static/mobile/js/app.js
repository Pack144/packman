import { claimCacheFor } from "./api.js";
import { icons, myDensLabel } from "./components.js";
import { initInstall } from "./install.js";
import { initMenu, menuLayer } from "./menu.js";
import { route, startRouter } from "./router.js";
import { renderHome } from "./screens/home.js";
import { renderMyDens } from "./screens/my-dens.js";
import { renderDens, renderDenDetail } from "./screens/dens.js";
import { renderSearch } from "./screens/search.js";
import { renderProfile } from "./screens/profile.js";
import { renderCommittees, renderCommitteeDetail } from "./screens/committees.js";

const TABS = [
  { key: "home", label: "Home", path: "/home", icon: icons.home },
  { key: "my-dens", label: "My Dens", path: "/my-dens", icon: icons.myDens },
  { key: "dens", label: "Dens", path: "/dens", icon: icons.dens },
  { key: "search", label: "Search", path: "/search", icon: icons.search },
  // No `path`: this tab opens the Me/Committees popover in place instead of
  // navigating (see menu.js), so it's rendered as a button below.
  { key: "menu", label: "Menu", icon: icons.menu },
];

function tabLabel(tab) {
  return tab.key === "my-dens" ? myDensLabel() : tab.label;
}

function tabMarkup(tab, activeKey) {
  const on = tab.key === activeKey;
  if (!tab.path) {
    // The Menu tab: a button that toggles the popover (menu.js) rather than
    // a link, so it needs the current route baked in as data-active — the
    // popover reads it back to decide whether to stay highlighted on close.
    return `
      <button type="button" class="tab${on ? " on" : ""}" id="menu-tab" data-active="${on}">
        ${tab.icon}${tabLabel(tab)}
      </button>`;
  }
  return `
    <a class="tab${on ? " on" : ""}" href="#${tab.path}">
      ${tab.icon}${tabLabel(tab)}
    </a>`;
}

function renderShell(activeKey) {
  // Static TABS constants only; no user data interpolated here.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  document.getElementById("app").innerHTML = `
    <div id="screen" class="screen"></div>
    <nav class="tbar">
      ${TABS.map((tab) => tabMarkup(tab, activeKey)).join("")}
    </nav>
    ${menuLayer()}
  `;
}

window.addEventListener("packman:den-count", () => {
  const tab = document.querySelector('.tbar a[href="#/my-dens"]');
  const spec = TABS.find((t) => t.key === "my-dens");
  // Static TABS constants only; no user data interpolated here.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  if (tab && spec) tab.innerHTML = `${spec.icon}${tabLabel(spec)}`;
});

// The screen currently on display, so a background data refresh knows what to
// repaint — and knows to give up if the reader has since navigated away.
let activeMount = null;

async function paint(renderFn, screen) {
  try {
    await renderFn(screen);
  } catch (err) {
    screen.innerHTML = '<p class="error">Something went wrong loading this screen.</p>';
    console.error(err);
  }
}

async function mount(renderFn, activeKey) {
  renderShell(activeKey);
  const screen = document.getElementById("screen");
  screen.innerHTML = '<p class="loading">Loading&hellip;</p>';
  const token = { renderFn };
  activeMount = token;
  await paint(renderFn, screen);
  if (activeMount !== token) return;
  const scroller = screen.querySelector(".screen-scroll");
  if (scroller) scroller.scrollTo(0, 0);
}

// A background revalidation turned up newer data than we painted from cache.
// Repaint in place, holding the reader's scroll position.
window.addEventListener("packman:data-refresh", async () => {
  const token = activeMount;
  const screen = document.getElementById("screen");
  if (!token || !screen) return;
  // Don't yank the page out from under someone typing (the search field).
  if (document.activeElement && document.activeElement.matches("input, textarea")) return;

  const offset = screen.querySelector(".screen-scroll")?.scrollTop ?? 0;
  await paint(token.renderFn, screen);
  if (activeMount !== token) return;
  const scroller = screen.querySelector(".screen-scroll");
  if (scroller) scroller.scrollTop = offset;
});

route("/home", () => mount(renderHome, "home"));
route("/my-dens", () => mount(renderMyDens, "my-dens"));
route("/dens", () => mount(renderDens, "dens"));
route("/dens/:number", (params) => mount((el) => renderDenDetail(el, params.number), "dens"));
route("/search", () => mount(renderSearch, "search"));
route("/me", () => mount((el) => renderProfile(el, window.PACKMAN_MOBILE.user.slug, { me: true }), "menu"));
route("/profile/:slug", (params) => mount((el) => renderProfile(el, params.slug), null));
route("/committees", () => mount(renderCommittees, "menu"));
route("/committees/:slug", (params) => mount((el) => renderCommitteeDetail(el, params.slug), "menu"));

// Drop any directory data cached for a different member before it can render.
claimCacheFor(window.PACKMAN_MOBILE.user.slug);

startRouter();

initInstall();
initMenu();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/mobile/sw.js", { scope: "/mobile/" }).catch((err) => {
      console.error("Service worker registration failed", err);
    });
  });
}
