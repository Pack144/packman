import { refreshAllData } from "./api.js";
import { icons } from "./components.js";

// The popover + its backdrop, appended to the shell on every mount. Both start
// hidden; opening/closing toggles the `hidden` attribute in place rather than
// re-rendering, so it survives independently of whatever screen is mounted.
export function menuLayer() {
  // Static markup and icon constants only; no user data interpolated here.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  return `
    <div class="menu-backdrop" id="menu-backdrop" hidden></div>
    <div class="menu-popover" id="menu-popover" hidden>
      <a class="menu-item" href="#/me">${icons.me}<span>Me</span></a>
      <a class="menu-item" href="#/committees">${icons.committees}<span>Committees</span></a>
      <button type="button" class="menu-item" id="menu-refresh">${icons.refresh}<span>Refresh Data</span></button>
    </div>
  `;
}

function setOpen(open) {
  const tab = document.getElementById("menu-tab");
  document.getElementById("menu-backdrop")?.toggleAttribute("hidden", !open);
  document.getElementById("menu-popover")?.toggleAttribute("hidden", !open);
  // Stay highlighted while open, and fall back to whether we're already on a
  // menu screen (Me/Committees) once it closes, rather than always going grey.
  if (tab) tab.classList.toggle("on", open || tab.dataset.active === "true");
}

async function handleRefresh(button) {
  if (button.disabled) return;
  button.disabled = true;
  const label = button.querySelector("span");
  if (label) label.textContent = "Refreshing…";
  // refreshAllData() ends in a page reload, so control doesn't normally come
  // back here — this is just a safety net if that ever changes.
  await refreshAllData();
}

/**
 * Wires the Menu tab's popover. Bound once to #app, which survives every
 * renderShell() rebuild — the same delegation pattern install.js uses for the
 * install banner.
 */
export function initMenu() {
  document.getElementById("app").addEventListener("click", (event) => {
    if (event.target.closest("#menu-tab")) {
      setOpen(document.getElementById("menu-popover")?.hasAttribute("hidden"));
      return;
    }
    const refreshButton = event.target.closest("#menu-refresh");
    if (refreshButton) {
      handleRefresh(refreshButton);
      return;
    }
    if (event.target.closest("#menu-backdrop") || event.target.closest(".menu-item")) {
      setOpen(false);
    }
  });
}
