import { route, startRouter } from "./router.js";
import { renderHome } from "./screens/home.js";
import { renderMyDens } from "./screens/my-dens.js";
import { renderDens, renderDenDetail } from "./screens/dens.js";
import { renderSearch } from "./screens/search.js";
import { renderProfile } from "./screens/profile.js";

const TABS = [
  { key: "home", label: "Home", path: "/home" },
  { key: "my-dens", label: "My Dens", path: "/my-dens" },
  { key: "dens", label: "Dens", path: "/dens" },
  { key: "search", label: "Search", path: "/search" },
  { key: "me", label: "Me", path: "/me" },
];

function renderShell(activeKey) {
  document.getElementById("app").innerHTML = `
    <header class="app-header">
      <span class="app-title">Pack Directory</span>
    </header>
    <main id="screen" class="screen-body"></main>
    <nav class="tabs">
      ${TABS.map(
        (tab) => `
        <a class="tab${tab.key === activeKey ? " on" : ""}" href="#${tab.path}">
          <span class="ic"></span>${tab.label}
        </a>`
      ).join("")}
    </nav>
  `;
}

async function mount(renderFn, activeKey) {
  renderShell(activeKey);
  const screen = document.getElementById("screen");
  screen.innerHTML = '<p class="loading">Loading&hellip;</p>';
  try {
    await renderFn(screen);
  } catch (err) {
    screen.innerHTML = '<p class="error">Something went wrong loading this screen.</p>';
    console.error(err);
  }
  screen.scrollTo(0, 0);
}

route("/home", () => mount(renderHome, "home"));
route("/my-dens", () => mount(renderMyDens, "my-dens"));
route("/dens", () => mount(renderDens, "dens"));
route("/dens/:number", (params) => mount((el) => renderDenDetail(el, params.number), "dens"));
route("/search", () => mount(renderSearch, "search"));
route("/me", () => mount((el) => renderProfile(el, window.PACKMAN_MOBILE.user.slug), "me"));
route("/profile/:slug", (params) => mount((el) => renderProfile(el, params.slug), null));

startRouter();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/mobile/sw.js", { scope: "/mobile/" }).catch((err) => {
      console.error("Service worker registration failed", err);
    });
  });
}
