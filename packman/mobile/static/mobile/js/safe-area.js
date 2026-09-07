import { isIos, isStandalone } from "./install.js";

// #app declares --safe-top/--safe-right/--safe-bottom/--safe-left from env() and
// is the only thing in the stylesheet that consumes the safe-area insets. That
// is correct whenever the viewport really does extend under the status bar and
// the home indicator.
//
// Installed on iOS it sometimes doesn't: the system hands the web view a
// viewport that has already had the insets taken out of it, while env() goes on
// reporting them. Padding by env() then counts them twice — the tab bar ends up
// a full inset clear of the screen edge, stranded above a band no CSS inside the
// page can reach. This measures whether that is happening and, if so, zeroes the
// two vertical vars so the insets are honoured exactly once.
//
// Everything here is a no-op unless the app is running standalone on iOS.

// The viewport is treated as pre-inset when the screen/viewport gap accounts for
// the reported insets. A couple of px of rounding slack; anything further off is
// some other cause and we leave the env() values alone rather than guess.
const TOLERANCE_PX = 2;

let probe = null;
let frame = 0;

// env() can't be read from JS, so park a hidden element that pads by it and read
// the padding back. Kept and reused rather than rebuilt per measurement.
function insetProbe() {
  if (!probe) {
    probe = document.createElement("div");
    probe.style.cssText =
      "position:fixed;top:0;left:0;width:0;height:0;visibility:hidden;pointer-events:none;" +
      "padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);";
    document.body.appendChild(probe);
  }
  const style = getComputedStyle(probe);
  return {
    top: parseFloat(style.paddingTop) || 0,
    bottom: parseFloat(style.paddingBottom) || 0,
  };
}

function measure() {
  const app = document.getElementById("app");
  if (!app) return;

  const { top, bottom } = insetProbe();

  // Nothing to double-count.
  if (top + bottom === 0) return;

  // screen.width/height don't swap on iOS when the device rotates, so pick the
  // physical extent that matches the current orientation rather than trusting
  // screen.height to be the one running the same way as innerHeight.
  const landscape = window.innerWidth > window.innerHeight;
  const screenHeight = landscape
    ? Math.min(window.screen.width, window.screen.height)
    : Math.max(window.screen.width, window.screen.height);

  const gap = screenHeight - window.innerHeight;
  const preInset = Math.abs(gap - (top + bottom)) <= TOLERANCE_PX;

  // Idempotent: re-running with the same geometry rewrites the same values, and
  // clearing lets the stylesheet's env() defaults take back over.
  if (preInset) {
    app.style.setProperty("--safe-top", "0px");
    app.style.setProperty("--safe-bottom", "0px");
  } else {
    app.style.removeProperty("--safe-top");
    app.style.removeProperty("--safe-bottom");
  }
}

function schedule() {
  if (frame) return;
  frame = requestAnimationFrame(() => {
    frame = 0;
    measure();
  });
}

export function initSafeArea() {
  // The gap this looks for also opens up in a plain Safari tab, where it's the
  // toolbars rather than the safe areas doing the shrinking — zeroing the insets
  // there would break a viewport that was fine. Standalone-on-iOS only.
  if (!isIos() || !isStandalone()) return;

  measure();
  window.addEventListener("orientationchange", schedule);
  window.addEventListener("resize", schedule);
  // Follows the insets more closely than resize does when the system chrome moves.
  if (window.visualViewport) window.visualViewport.addEventListener("resize", schedule);
}
