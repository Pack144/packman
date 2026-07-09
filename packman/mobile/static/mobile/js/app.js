import { icons, myDensLabel } from "./components.js";
import { route, startRouter } from "./router.js";
import { renderHome } from "./screens/home.js";
import { renderMyDens } from "./screens/my-dens.js";
import { renderDens, renderDenDetail } from "./screens/dens.js";
import { renderSearch } from "./screens/search.js";
import { renderProfile } from "./screens/profile.js";

const TABS = [
  { key: "home", label: "Home", path: "/home", icon: icons.home },
  { key: "my-dens", label: "My Dens", path: "/my-dens", icon: icons.myDens },
  { key: "dens", label: "Dens", path: "/dens", icon: icons.dens },
  { key: "search", label: "Search", path: "/search", icon: icons.search },
  { key: "me", label: "Me", path: "/me", icon: icons.me },
];

function tabLabel(tab) {
  return tab.key === "my-dens" ? myDensLabel() : tab.label;
}

function renderShell(activeKey) {
  // Static TABS constants only; no user data interpolated here.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  document.getElementById("app").innerHTML = `
    <div id="screen" class="screen"></div>
    <nav class="tbar">
      ${TABS.map(
        (tab) => `
        <a class="tab${tab.key === activeKey ? " on" : ""}" href="#${tab.path}">
          ${tab.icon}${tabLabel(tab)}
        </a>`
      ).join("")}
    </nav>
  `;
}

window.addEventListener("packman:den-count", () => {
  const tab = document.querySelector('.tbar a[href="#/my-dens"]');
  const spec = TABS.find((t) => t.key === "my-dens");
  // Static TABS constants only; no user data interpolated here.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  if (tab && spec) tab.innerHTML = `${spec.icon}${tabLabel(spec)}`;
});

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
  const scroller = screen.querySelector(".screen-scroll");
  if (scroller) scroller.scrollTo(0, 0);
}

route("/home", () => mount(renderHome, "home"));
route("/my-dens", () => mount(renderMyDens, "my-dens"));
route("/dens", () => mount(renderDens, "dens"));
route("/dens/:number", (params) => mount((el) => renderDenDetail(el, params.number), "dens"));
route("/search", () => mount(renderSearch, "search"));
route("/me", () => mount((el) => renderProfile(el, window.PACKMAN_MOBILE.user.slug, { me: true }), "me"));
route("/profile/:slug", (params) => mount((el) => renderProfile(el, params.slug), null));

startRouter();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/mobile/sw.js", { scope: "/mobile/" }).catch((err) => {
      console.error("Service worker registration failed", err);
    });
  });
}
