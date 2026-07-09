import { appBar, denBadge, esc, initialsOf, pluralize, setMyDenCount } from "../components.js";
import { api } from "../api.js";

function packDigits(packName) {
  const match = (packName || "").match(/\d+/);
  return match
    ? `<div class="brand-digits">${[...match[0]].map((d) => `<span>${d}</span>`).join("")}</div>`
    : "";
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
            ${denBadge(cub.rank_key, cub.rank_badge, "sm")}
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

export async function renderHome(container) {
  const data = await api.home();

  const denNumbers = new Set(
    (data.family?.children || []).map((cub) => cub.den_number).filter((n) => n !== null)
  );
  const singleDen = denNumbers.size === 1;
  setMyDenCount(denNumbers.size);

  container.innerHTML = `
    ${appBar(`
      ${packDigits(data.pack.name)}
      <div style="line-height:1.05">
        <div class="brand-name">${esc(data.pack.name)}</div>
        <div class="brand-sub">${esc(data.pack.location)}</div>
      </div>
      <a class="appbar-avatar" href="#/me">${esc(initialsOf(data.user.name)[0] || "?")}</a>
    `)}
    <div class="screen-scroll">
      <div>
        <h1 class="h1red">Hi, ${esc(data.user.short_name)}</h1>
        ${data.family ? `<div class="h1sub">${esc(data.family.name)}</div>` : ""}
      </div>
      ${familyCard(data.family)}
      ${eventCard(data.event)}
      <section>
        <h2 class="sect">Jump To</h2>
        <div class="card row-divided">
          <a class="row" href="#/my-dens"><span class="den-badge" style="width:34px;height:34px;background:#2f6fb0">W</span><div class="row-title">My Den${singleDen ? "" : "s"}</div><span class="chev">&rsaquo;</span></a>
          <a class="row" href="#/dens"><span class="den-badge" style="width:34px;height:34px;background:#1a4aa0">D</span><div class="row-title">All Dens in Pack</div><span class="chev">&rsaquo;</span></a>
          <a class="row" href="#/search"><span class="den-badge" style="width:34px;height:34px;background:#20242b">Q</span><div class="row-title">Search Directory</div><span class="chev">&rsaquo;</span></a>
        </div>
      </section>
    </div>
  `;
}
