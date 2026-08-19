import { preloadCriticalData } from "./api.js";
import { icons } from "./components.js";

// Whoever waves the banner away means it; don't ask again on this device.
const DISMISSED_KEY = "packman:install-dismissed";

// Chrome hands the install prompt over through `beforeinstallprompt` and nowhere
// else, so we hold onto the event until someone taps Install. Safari never fires
// it, which is what splits the banner into its two forms below.
let deferredPrompt = null;

function isStandalone() {
  // navigator.standalone is the iOS-only spelling, and the only one Safari sets.
  return (
    window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true
  );
}

function isIos() {
  // iPadOS 13+ reports itself as a Mac; the touch points are what give it away.
  return (
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

function isDismissed() {
  try {
    return localStorage.getItem(DISMISSED_KEY) === "1";
  } catch {
    // Private browsing blocks storage; the banner just returns next launch.
    return false;
  }
}

function dismiss() {
  try {
    localStorage.setItem(DISMISSED_KEY, "1");
  } catch {
    // Nothing to persist to — the repaint below still clears it for this visit.
  }
  paintInstallSlot();
}

/**
 * The Home banner, in whichever form this browser can act on — or an empty
 * string where installing isn't on offer (already installed, waved away, or a
 * desktop browser with nowhere to install to).
 */
export function installBanner() {
  if (isStandalone() || isDismissed()) return "";

  const dismissButton = '<button class="install-x" data-install-dismiss aria-label="Not now">&times;</button>';

  // Chrome and Edge: a real button, because we're holding a live prompt.
  if (deferredPrompt) {
    return `
      <div class="install-banner card">
        ${icons.install}
        <div class="grow">
          <div class="install-title">Install Pack Directory</div>
          <div class="install-sub">Keep the directory on hand, even offline.</div>
        </div>
        <button class="install-btn" data-install>Install</button>
        ${dismissButton}
      </div>
    `;
  }

  // Safari can't be prompted at all, so the banner has to walk through the
  // manual route instead of offering a button that couldn't do anything.
  if (isIos()) {
    return `
      <div class="install-banner card">
        ${icons.install}
        <div class="grow">
          <div class="install-title">Install Pack Directory</div>
          <div class="install-sub">Tap ${icons.share} Share, then &ldquo;Add to Home Screen&rdquo;.</div>
        </div>
        ${dismissButton}
      </div>
    `;
  }

  return "";
}

/** Repaint the banner in place after something changes what it should say. */
export function paintInstallSlot() {
  const slot = document.getElementById("install-slot");
  // Static markup and icon constants only; no user data interpolated here.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  if (slot) slot.innerHTML = installBanner();
}

export function initInstall() {
  window.addEventListener("beforeinstallprompt", (event) => {
    // Suppress Chrome's own mini-infobar in favour of the in-app banner, which
    // sits where the reader is already looking.
    event.preventDefault();
    deferredPrompt = event;
    // The event lands whenever Chrome decides it does, which is often after Home
    // has already painted — hence the repaint rather than a render-time check.
    paintInstallSlot();
  });

  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    paintInstallSlot();
    // Fill the caches now, while we know there's a network, rather than leaving
    // the first offline launch to find them empty.
    preloadCriticalData();
  });

  // The shell is rebuilt on every navigation, so the listener lives on #app —
  // the one element inside the page that survives it.
  document.getElementById("app").addEventListener("click", (event) => {
    if (event.target.closest("[data-install-dismiss]")) {
      dismiss();
      return;
    }
    if (!event.target.closest("[data-install]")) return;

    // The prompt is single-use: calling it twice throws, and Chrome re-offers it
    // on a later visit if this one is declined. Let it go before prompting so a
    // double tap can't reach it.
    const prompt = deferredPrompt;
    deferredPrompt = null;
    paintInstallSlot();
    prompt?.prompt();
  });

  // iOS never fires `appinstalled`, so a standalone launch is the only word we
  // get that the app was installed. Warm the caches the directory reads from.
  if (isStandalone()) preloadCriticalData();
}
