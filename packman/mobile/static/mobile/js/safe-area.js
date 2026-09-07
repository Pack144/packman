import { isIos, isStandalone } from "./install.js";

// #app declares --safe-top/--safe-right/--safe-bottom/--safe-left from env() and
// is the only thing in the stylesheet that consumes the safe-area insets. That
// is correct whenever the viewport really does extend under the system UI.
//
// Installed on iOS it may not. Measured on an iPhone 16 Pro (402x874pt) running
// standalone: screen.height 874 against innerHeight 812, with env() reporting
// 62px top and 34px bottom. The viewport had the *top* inset taken out of it
// already — it starts below the status bar — while still extending under the
// home indicator, and env() went on reporting both. Padding by env() there adds
// the top inset a second time: 62px of dead band above an app bar that was
// already clear of the status bar.
//
// So the two edges have to be decided separately. The screen/viewport gap says
// how much the system took out; which insets sum to that gap says which edges it
// took it from. An edge the system already handled gets zeroed here; an edge it
// left to us keeps its env() value.
//
// All of this is a no-op unless the app is running standalone on iOS.

// Slack for rounding when matching the gap against a combination of insets.
// Anything further out than this is a geometry we don't recognise, and we leave
// env() alone rather than guess at it.
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

// Which edges the system has already taken out of the viewport, or null if the
// gap doesn't correspond to any combination of the reported insets.
function preInsetEdges(gap, top, bottom) {
  const splits = [
    { top: false, bottom: false, total: 0 },
    { top: true, bottom: false, total: top },
    { top: false, bottom: true, total: bottom },
    { top: true, bottom: true, total: top + bottom },
  ];

  let best = null;
  let bestError = Infinity;
  for (const split of splits) {
    const error = Math.abs(gap - split.total);
    // Ties go to the earlier entry, so a device whose two insets happen to be
    // equal is read as top-inset — the case iOS actually produces.
    if (error < bestError) {
      bestError = error;
      best = split;
    }
  }
  return bestError <= TOLERANCE_PX ? best : null;
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

  const edges = preInsetEdges(screenHeight - window.innerHeight, top, bottom);
  if (!edges) return;

  // Idempotent: re-running with the same geometry rewrites the same values, and
  // clearing an edge lets the stylesheet's env() default take back over.
  for (const [name, preInset] of [
    ["--safe-top", edges.top],
    ["--safe-bottom", edges.bottom],
  ]) {
    if (preInset) app.style.setProperty(name, "0px");
    else app.style.removeProperty(name);
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
  // The gap this reads also opens up in a plain Safari tab, where it's the
  // toolbars rather than the safe areas doing the shrinking — zeroing an inset
  // there would break a viewport that was fine. Standalone-on-iOS only.
  if (!isIos() || !isStandalone()) return;

  measure();
  window.addEventListener("orientationchange", schedule);
  window.addEventListener("resize", schedule);
  // Follows the insets more closely than resize does when the system chrome moves.
  if (window.visualViewport) window.visualViewport.addEventListener("resize", schedule);
}
