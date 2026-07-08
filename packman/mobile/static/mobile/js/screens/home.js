import { avatar, badge, chip, esc, pluralize } from "../components.js";
import { api } from "../api.js";

export async function renderHome(container) {
  const data = await api.home();
  const family = data.family;

  const familyCard = family
    ? `
    <div class="card family-card">
      <div class="row">
        <div class="avatar-stack">
          ${family.adults.map((a) => avatar(a.avatar, a.name, "md")).join("")}
        </div>
        <div class="col">
          <div class="row-title lg">${esc(family.name)}</div>
          <span class="mono">YOUR FAMILY</span>
        </div>
      </div>
      <div class="row chip-row">
        ${family.dens.map((d) => chip(d)).join("")}
        ${chip(pluralize(family.children.length, "Cub"))}
      </div>
      ${
        family.children.length
          ? `<div class="row chip-row">
        ${family.children
          .map(
            (cub) => `
          <a class="card cub-card" href="#/profile/${encodeURIComponent(cub.slug)}">
            <div class="row">
              ${avatar(cub.avatar, cub.name, "sm")}
              <div class="col"><div class="row-title">${esc(cub.name)}</div></div>
              ${badge(cub.rank_letter)}
            </div>
          </a>`
          )
          .join("")}
      </div>`
          : ""
      }
    </div>
  `
    : `<p class="empty">You're not linked to a family yet. Reach out to Pack leadership if that looks wrong.</p>`;

  container.innerHTML = `
    <h1 class="hi">Hi, ${esc(data.user.name.split(" ")[0])}</h1>
    ${familyCard}
    <span class="mono section-label">JUMP TO</span>
    <div class="card list-card">
      <a class="row" href="#/my-dens"><span class="row-title">My Dens</span><span class="chev">&rsaquo;</span></a>
      <hr class="hr">
      <a class="row" href="#/dens"><span class="row-title">All Dens in Pack</span><span class="chev">&rsaquo;</span></a>
      <hr class="hr">
      <a class="row" href="#/search"><span class="row-title">Search directory</span><span class="chev">&rsaquo;</span></a>
    </div>
  `;
}
