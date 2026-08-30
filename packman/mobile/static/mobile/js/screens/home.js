import { appBar, avatar, esc, initialsOf, pluralize, setMyDenCount } from "../components.js";
import {
  api,
  currentAkela,
  getDirectory,
  getFamilyRequirements,
  myActiveChildren,
  myFamilyCard,
} from "../api.js";
import { installBanner } from "../install.js";

function packDigits(packName) {
  const match = (packName || "").match(/\d+/);
  return match
    ? `<div class="brand-digits">${[...match[0]].map((d) => `<span>${d}</span>`).join("")}</div>`
    : "";
}

function userAvatar(user) {
  const inner = user.avatar
    ? `<img src="${esc(user.avatar)}" alt="${esc(user.name)}">`
    : esc(initialsOf(user.name) || "?");
  return `<a class="appbar-avatar" href="#/me" aria-label="Your profile">${inner}</a>`;
}

function eventCard(event) {
  if (!event) {
    return `
    <section>
      <h2 class="sect red">Coming Up</h2>
      <div class="card"><p class="empty" style="padding:14px 15px;margin:0">Nothing on the calendar just yet.</p></div>
    </section>
  `;
  }
  const start = new Date(event.start);
  const dateLine = start.toLocaleDateString([], { weekday: "short", month: "long", day: "numeric" });
  const time = (d) =>
    new Date(d).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }).replace(" ", "").toLowerCase();
  const when = event.end ? `${time(event.start)}–${time(event.end)}` : time(event.start);
  return `
    <section>
      <h2 class="sect red">Coming Up</h2>
      <div class="event-card">
        <div class="event-date">${esc(dateLine)}</div>
        <div class="event-name">${esc(event.name)}</div>
        <div class="event-when">${esc(when)}${event.location ? ` · ${esc(event.location)}` : ""}</div>
        ${event.description ? `<div class="event-desc">${esc(event.description)}</div>` : ""}
      </div>
    </section>
  `;
}

function familyCard(family) {
  if (!family) {
    return '<p class="empty">You’re not linked to a family yet. Reach out to Pack leadership if that looks wrong.</p>';
  }
  const sub = [pluralize(family.children.length, "Cub"), family.dens.join(" & ")].filter(Boolean).join(" · ");
  return `
    <div class="card">
      <div class="family-card-hero">
        <div class="overlay"></div>
        <div class="caption">
          <div class="fam-name">${esc(family.name)}</div>
          <div class="fam-sub">${esc(sub)}</div>
        </div>
      </div>
      ${
        family.children.length
          ? `<div class="cub-chips">
        ${family.children
          .map(
            (cub) => `
          <a class="cub-chip" href="#/profile/${encodeURIComponent(cub.slug)}">
            ${avatar(cub.avatar, cub.name, "sm")}
            <div class="grow">
              <div class="cub-name">${esc(cub.name)}</div>
              <div class="mono">${esc(cub.den_label || "")}</div>
            </div>
          </a>`
          )
          .join("")}
      </div>`
          : ""
      }
    </div>
  `;
}

// The Pack's Akela leads the Jump To card. currentAkela() guarantees a
// linked member (or null), so this always renders a live profile link.
function akelaRow(akela) {
  if (!akela) return "";
  const inner = `
    ${avatar(akela.avatar, akela.name, "sm")}
    <div class="grow">
      <div class="row-title">${esc(akela.name)}</div>
      <div class="mono plain">${esc(akela.title)}</div>
    </div>
  `;
  return `<a class="row" href="#/profile/${encodeURIComponent(akela.slug)}">${inner}<span class="chev">&rsaquo;</span></a>`;
}

/**
 * A nudge when the family owes paperwork, linking through to the detail on
 * Me. Silent when everything is in order — Home shouldn't carry a banner
 * saying nothing is wrong.
 */
function requirementsNotice(requirements) {
  if (!requirements?.outstanding) return "";
  const count = requirements.outstanding;
  return `
    <a class="notice warn card" href="#/me">
      <span class="notice-dot" aria-hidden="true"></span>
      <div class="grow">
        <div class="notice-title">${count} membership ${
          count === 1 ? "requirement needs" : "requirements need"
        } attention</div>
        <div class="notice-sub">Tap to see what's outstanding for your family.</div>
      </div>
      <span class="chev">&rsaquo;</span>
    </a>
  `;
}

export async function renderHome(container) {
  // getFamilyRequirements() resolves null rather than throwing, so a failed
  // or offline call just drops the notice instead of taking Home down.
  const [directory, { event }, requirements] = await Promise.all([
    getDirectory(),
    api.event(),
    getFamilyRequirements(),
  ]);
  const user = directory.me;
  const family = myFamilyCard(directory);
  const akela = currentAkela(directory);

  const denNumbers = new Set(myActiveChildren(directory).map((cub) => cub.den_number).filter((n) => n !== null));
  const singleDen = denNumbers.size === 1;
  setMyDenCount(denNumbers.size);

  // User-supplied values are escaped via esc() before interpolation.
  // nosemgrep: javascript.browser.security.insecure-document-method, javascript.browser.security.insecure-innerhtml
  container.innerHTML = `
    ${appBar(`
      ${packDigits(directory.pack.name)}
      <div style="line-height:1.05">
        <div class="brand-name">${esc(directory.pack.name)}</div>
        <div class="brand-sub">${esc(directory.pack.location)}</div>
      </div>
      ${userAvatar(user)}
    `)}
    <div class="screen-scroll">
      <div>
        <h1 class="h1red">Hi, ${esc(user.short_name)}</h1>
        ${family ? `<div class="h1sub">${esc(family.name)}</div>` : ""}
      </div>
      <div id="install-slot">${installBanner()}</div>
      ${requirementsNotice(requirements)}
      ${familyCard(family)}
      ${eventCard(event)}
      <section>
        <h2 class="sect">Jump To</h2>
        <div class="card row-divided">
          ${akelaRow(akela)}
          <a class="row" href="#/my-dens"><span class="den-badge" style="width:34px;height:34px;background:var(--rank-wolf)">W</span><div class="row-title">My Den${singleDen ? "" : "s"}</div><span class="chev">&rsaquo;</span></a>
          <a class="row" href="#/dens"><span class="den-badge" style="width:34px;height:34px;background:var(--rank-webelos)">D</span><div class="row-title">All Dens in Pack</div><span class="chev">&rsaquo;</span></a>
          <a class="row" href="#/search"><span class="den-badge" style="width:34px;height:34px;background:var(--badge-neutral)">Q</span><div class="row-title">Search Directory</div><span class="chev">&rsaquo;</span></a>
        </div>
      </section>
    </div>
  `;
}
